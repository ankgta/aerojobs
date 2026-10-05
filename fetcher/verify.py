"""Check candidate employer sources without changing any data.

    python -m fetcher.verify config/candidates.yaml

For each candidate it asks the hiring system for its open jobs and records how many it
found, a few sample titles and locations (to confirm it is the right company), and any
error. The result goes to data/verify_report.json. Nothing is switched on.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from .common import DATA_DIR, load_employers, now_iso
from .connectors import CONNECTORS
from .http import PoliteClient, RobotsBlocked

REPORT = DATA_DIR / "verify_report.json"


def check(client: PoliteClient, emp: dict) -> dict:
    src = emp.get("source") or {}
    out = {"name": emp["name"], "slug": emp["slug"], "source": src, "ok": False}
    list_fn, detail_fn = CONNECTORS.get(src.get("ats"), (None, None))
    if not list_fn:
        out["error"] = f"unknown hiring system {src.get('ats')!r}"
        return out
    try:
        jobs = list_fn(client, src, 400)
    except RobotsBlocked as e:
        out["error"] = f"robots.txt blocks it: {e}"
        return out
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return out
    out["jobs_found"] = len(jobs)
    out["sample"] = [{"title": j.get("title"), "location": j.get("location"), "url": j.get("url"),
                      "posted": j.get("posted_date")} for j in jobs[:6]]
    if detail_fn and jobs:
        try:
            d = detail_fn(client, jobs[0])
            out["detail_sample"] = {k: d.get(k) for k in ("country_code", "posted_date", "closing_date",
                                                          "work_mode", "employment_type", "location")}
        except Exception as e:
            out["detail_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    out["ok"] = len(jobs) > 0
    return out


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    path = Path(argv[0]) if argv else Path("config/candidates.yaml")
    client = PoliteClient(delay=1.5)
    results = []
    for emp in load_employers(path):
        print(f"- {emp['name']}", flush=True)
        try:
            r = check(client, emp)
        except Exception:
            r = {"name": emp["name"], "slug": emp["slug"], "ok": False, "error": traceback.format_exc(limit=1)[-300:]}
        print(f"  {'OK ' + str(r.get('jobs_found')) + ' jobs' if r['ok'] else r.get('error', 'no jobs')}", flush=True)
        results.append(r)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"run": now_iso(), "results": results}, indent=1, ensure_ascii=False))
    print(f"\n{sum(r['ok'] for r in results)} of {len(results)} candidates returned jobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
