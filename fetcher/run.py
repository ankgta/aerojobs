"""The job fetcher. Run with:  python -m fetcher.run

Reads every enabled employer, updates data/jobs.json, marks jobs that have
disappeared as expired, and writes data/alerts.json for anything that needs a look.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import traceback

from .common import (DATA_DIR, safe_url, load_employers, load_site_config, now_iso, read_json,
                     short_hash, slugify, today, write_json)
from .connectors import CONNECTORS
from .geo import country_from_location, country_name, is_country_code, region_of
from .http import PoliteClient, RobotsBlocked
from .roles import (DEFAULT_ROLE, ai_classify, classify_title, detect_work_mode,
                    normalize_employment_type)

JOBS_FILE = DATA_DIR / "jobs.json"
STATUS_FILE = DATA_DIR / "employer_status.json"
ROLE_CACHE_FILE = DATA_DIR / "role_cache.json"
ALERTS_FILE = DATA_DIR / "alerts.json"


def job_id(employer_slug: str, source_id: str) -> str:
    return f"{employer_slug}-{short_hash(source_id, 10)}"


def apply_fields(rec: dict, raw: dict, employer: dict) -> None:
    """Copy what a source told us onto a stored job and work out the derived fields."""
    for key in ("title", "location", "closing_date", "department"):
        if raw.get(key):
            rec[key] = raw[key]
    if raw.get("url") and safe_url(raw["url"]):
        rec["url"] = safe_url(raw["url"])
    if raw.get("posted_date") and (rec.get("posted_estimated", True) or raw.get("posted_estimated") is False):
        rec["posted_date"] = raw["posted_date"]
        rec["posted_estimated"] = bool(raw.get("posted_estimated"))
    if raw.get("employment_type"):
        rec["employment_type"] = normalize_employment_type(raw["employment_type"])
    code = raw.get("country_code")
    if code and is_country_code(code):
        rec["country_code"] = code.upper()
    elif not rec.get("country_code"):
        rec["country_code"] = country_from_location(rec.get("location"), employer.get("country"))
    rec["country"] = country_name(rec.get("country_code"))
    rec["region"] = region_of(rec.get("country_code")) if rec.get("country_code") else None
    rec["work_mode"] = detect_work_mode(rec.get("title"), rec.get("location"),
                                        structured=raw.get("work_mode") or rec.get("work_mode_source"))
    if raw.get("work_mode"):
        rec["work_mode_source"] = raw["work_mode"]
    if rec.get("title") and (rec.get("role_source") != "rules" or raw.get("title")):
        role = classify_title(rec["title"], employer.get("type"))
        if role:
            rec["role"], rec["role_source"] = role, "rules"
        elif rec.get("role_source") != "ai":
            rec["role"], rec["role_source"] = None, None


def merge_employer_jobs(jobs: dict, employer: dict, raws: list[dict], run_date: str,
                        expire_after: int = 2) -> list[dict]:
    """Add new jobs, refresh known ones, count misses and expire old ones. Returns new jobs."""
    slug = employer["slug"]
    seen, new = set(), []
    for raw in raws:
        jid = job_id(slug, raw["source_id"])
        if jid in seen:
            continue
        seen.add(jid)
        rec = jobs.get(jid)
        if rec is None:
            rec = {
                "id": jid,
                "employer": slug,
                "company": employer["name"],
                "company_type": employer.get("type", "other"),
                "source_id": raw["source_id"],
                "first_seen": run_date,
                "posted_date": run_date,
                "posted_estimated": True,
                "status": "active",
                "missed_runs": 0,
            }
            if raw.get("detail_url"):
                rec["detail_url"] = raw["detail_url"]
                rec["detail_pending"] = True
            jobs[jid] = rec
            new.append(rec)
        else:
            rec["missed_runs"] = 0
            if rec["status"] == "expired":
                rec["status"] = "active"
                rec.pop("expired_on", None)
        rec["last_seen"] = run_date
        apply_fields(rec, raw, employer)
        if not rec.get("slug") and rec.get("title"):
            rec["slug"] = f"{slugify(rec['title'], 60)}-{slug}-{short_hash(raw['source_id'], 6)}"
    for jid, rec in jobs.items():
        if rec["employer"] == slug and rec["status"] == "active" and jid not in seen:
            rec["missed_runs"] = rec.get("missed_runs", 0) + 1
            if rec["missed_runs"] >= expire_after:
                rec["status"] = "expired"
                rec["expired_on"] = run_date
    return new


def purge_expired(jobs: dict, keep_days: int, run_date: str) -> int:
    cutoff = (dt.date.fromisoformat(run_date) - dt.timedelta(days=keep_days)).isoformat()
    old = [jid for jid, r in jobs.items() if r["status"] == "expired" and r.get("expired_on", run_date) < cutoff]
    for jid in old:
        del jobs[jid]
    return len(old)


def is_visible(rec: dict) -> bool:
    return (rec.get("status") == "active" and bool(rec.get("title")) and bool(rec.get("slug"))
            and safe_url(rec.get("url")) is not None)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch aviation jobs from employer career sites.")
    ap.add_argument("--only", help="fetch just this employer slug")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, but do not save")
    args = ap.parse_args(argv)

    cfg = load_site_config()
    fc = cfg.get("fetch", {})
    run_date = today().isoformat()
    employers = [e for e in load_employers() if e.get("enabled") and e.get("source")]
    if args.only:
        employers = [e for e in employers if e["slug"] == args.only]
    if not employers:
        print("No employers are switched on yet (enabled: true with a source) in config/employers.yaml.")

    client = PoliteClient(delay=float(fc.get("delay_seconds", 1.5)))
    store = read_json(JOBS_FILE, {"jobs": {}})
    jobs = store["jobs"]
    status = read_json(STATUS_FILE, {})
    role_cache = read_json(ROLE_CACHE_FILE, {})
    alerts = []

    for emp in employers:
        src = emp["source"]
        ats = src.get("ats")
        if ats not in CONNECTORS:
            alerts.append({"employer": emp["name"], "problem": f"Unknown hiring system '{ats}' in config"})
            continue
        list_fn, detail_fn = CONNECTORS[ats]
        prev = status.get(emp["slug"], {})
        print(f"- {emp['name']} ({ats})", flush=True)
        try:
            raws = list_fn(client, src, int(fc.get("max_jobs_per_employer", 3000)))
        except RobotsBlocked as e:
            alerts.append({"employer": emp["name"], "problem": f"Site's robots.txt does not allow reading it: {e}"})
            status[emp["slug"]] = {**prev, "last_run": now_iso(), "last_error": str(e)}
            continue
        except Exception as e:  # any failure: skip, keep its jobs, report it
            print("  failed:", e)
            traceback.print_exc(limit=1)
            alerts.append({"employer": emp["name"], "problem": f"Could not read jobs: {e}"})
            status[emp["slug"]] = {**prev, "last_run": now_iso(), "last_error": str(e)}
            continue

        new = merge_employer_jobs(jobs, emp, raws, run_date, int(fc.get("expire_after_missed_runs", 2)))
        print(f"  {len(raws)} open, {len(new)} new")
        if not raws:
            alerts.append({"employer": emp["name"], "problem": "Returned zero jobs. Its careers page may have changed."})
        elif prev.get("last_count", 0) >= 20 and len(raws) < prev["last_count"] * 0.2:
            alerts.append({"employer": emp["name"],
                           "problem": f"Job count fell from {prev['last_count']} to {len(raws)}. Worth a check."})

        if detail_fn:
            pending = [r for r in jobs.values()
                       if r["employer"] == emp["slug"] and r.get("detail_pending") and r["status"] == "active"]
            limit = int(fc.get("max_new_details_per_employer", 250))
            failures = 0
            for rec in pending[:limit]:
                try:
                    fields = detail_fn(client, rec)
                except Exception as e:
                    failures += 1
                    if failures >= 5:
                        print(f"  stopped reading job pages after repeated errors: {e}")
                        break
                    continue
                apply_fields(rec, fields, emp)
                if not rec.get("slug") and rec.get("title"):
                    rec["slug"] = f"{slugify(rec['title'], 60)}-{emp['slug']}-{short_hash(rec['source_id'], 6)}"
                rec.pop("detail_pending", None)
            if len(pending) > limit:
                print(f"  {len(pending) - limit} job pages left for the next run")

        status[emp["slug"]] = {"last_run": now_iso(), "last_count": len(raws), "last_error": None}

    # Sort unclear titles with AI (only if a key is set), then fall back to the default group.
    unclear = [r for r in jobs.values() if is_visible(r) and not r.get("role")]
    if unclear:
        answers = ai_classify([r["title"] for r in unclear], role_cache, int(fc.get("ai_role_sorting_limit", 200)))
        for r in unclear:
            if r["title"] in answers:
                r["role"], r["role_source"] = answers[r["title"]], "ai"
            else:
                r["role"], r["role_source"] = DEFAULT_ROLE, "default"

    removed = purge_expired(jobs, int(fc.get("keep_expired_days", 30)), run_date)
    visible = sum(1 for r in jobs.values() if is_visible(r))
    print(f"\nDone: {visible} live jobs, {removed} old expired jobs removed, "
          f"{client.request_count} web requests, {len(alerts)} alerts.")

    if args.dry_run:
        print("Dry run: nothing saved.")
        return 0
    store["updated_at"] = now_iso()
    write_json(JOBS_FILE, store)
    write_json(STATUS_FILE, status)
    write_json(ROLE_CACHE_FILE, role_cache)
    write_json(ALERTS_FILE, {"run": now_iso(), "alerts": alerts})
    return 0


if __name__ == "__main__":
    sys.exit(main())
