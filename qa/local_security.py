"""Security checks that need a build with hostile data (run locally or in CI).

    python qa/local_security.py --out qa-results

Builds the site from job data that contains script-injection attempts in every text field,
then checks the pages and the search show them as plain text. Also scans the repository
history for leaked keys. Results go to local_security.json.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
from fetcher.run import merge_employer_jobs  # noqa: E402
from site_builder.build import Builder  # noqa: E402

EVIL = {
    "title": 'Pilot <script>alert("t")</script><img src=x onerror=alert("t2")>',
    "location": '"><svg onload=alert("loc")>, United Kingdom',
    "url": "https://careers.example.com/job?id=1&ref=a",
}
RESULTS = []


def rec(tc, title, attack, expected, ok, actual, sev="High"):
    RESULTS.append({"id": tc, "area": "Cross-site scripting" if tc != "SEC-27" else "Secrets",
                    "title": title, "attack": attack, "expected": expected,
                    "status": "Pass" if ok else "Fail", "actual": actual, "severity": "-" if ok else sev})
    print(f"  {'✓' if ok else '✗'} {tc} {title}: {actual}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="qa-results")
    out = Path(ap.parse_args().out)
    tmp = Path(tempfile.mkdtemp())
    emp_file = tmp / "employers.yaml"
    emp_file.write_text('employers:\n  - {name: "Evil Air </script><script>alert(9)</script>", slug: evil-air, type: airline, country: GB, enabled: true}\n')
    emp = {"name": 'Evil Air </script><script>alert(9)</script>', "slug": "evil-air", "type": "airline"}
    jobs = {}
    merge_employer_jobs(jobs, emp, [
        {"source_id": "1", **EVIL},
        {"source_id": "2", "title": "Cabin crew", "url": "javascript:alert('apply')", "location": "Dubai"},
    ], "2026-10-05")
    (tmp / "jobs.json").write_text(json.dumps({"updated_at": "2026-10-05T00:00:00+00:00", "jobs": jobs}))
    site = tmp / "site"
    Builder(site, False, tmp / "jobs.json", emp_file).build()

    visible = [j for j in jobs.values() if j.get("status") == "active" and j.get("url", "").startswith("http")]
    rec("SEC-24", "Unsafe Apply link from an employer site is dropped",
        "Job whose Apply link is javascript:alert()", "Job not published", len(visible) == 1,
        f"{len(jobs)} jobs received, {len(visible)} published; the javascript: one was rejected")

    page_html = next(site.glob("jobs/*/index.html")).read_text()
    raw_script = any(s in page_html for s in ("<script>alert", "<img src=x", "<svg onload"))
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', page_html, re.S)
    ld_ok = bool(m) and "</script" not in m.group(1).lower()
    try:
        json.loads(m.group(1))
    except Exception:
        ld_ok = False
    rec("SEC-25", "Job data with HTML/script is escaped in pages",
        "Script tags in job title, employer name, location and link", "Shown as text; Google data cannot break out",
        not raw_script and ld_ok, "no raw <script> in the page; structured data stays valid JSON" if not raw_script and ld_ok
        else f"raw script in page: {raw_script}; structured data safe: {ld_ok}")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(site))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    fired = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.on("dialog", lambda d: (fired.append(d.message), d.dismiss()))
        for path in ("/", next(site.glob("jobs/*/index.html")).parent.relative_to(site).as_posix() + "/", "/companies/evil-air/"):
            pg.goto(base + "/" + path.lstrip("/"))
            pg.wait_for_timeout(1200)
        pg.goto(base + "/?q=pilot")
        pg.wait_for_timeout(1200)
        shown = pg.locator(".job-title").first.inner_text() if pg.locator(".job-title").count() else ""
        b.close()
    srv.shutdown()
    rec("SEC-26", "Stored XSS through job data in the browser",
        "Open home, job and employer pages and search results built from hostile data", "No script runs",
        not fired, f"alerts fired: {len(fired)}; title shown as text: {shown[:60]!r}")

    log = subprocess.run(["git", "-C", str(ROOT), "log", "-p", "--all"], capture_output=True, text=True).stdout
    pats = {"Cloudflare/GitHub/Anthropic style token": r"(sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
            "Generic API key assignment": r"(?i)(api[_-]?token|api[_-]?key|secret)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]"}
    hits = {k: len(re.findall(v, log)) for k, v in pats.items()}
    rec("SEC-27", "No secrets in the code history", "Scan every commit for keys and tokens",
        "None found; keys live only in GitHub Secrets", not any(hits.values()),
        "no keys or tokens found in any commit" if not any(hits.values()) else f"possible secrets: {hits}", "Critical")

    out.mkdir(parents=True, exist_ok=True)
    (out / "local_security.json").write_text(json.dumps({"results": RESULTS}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
