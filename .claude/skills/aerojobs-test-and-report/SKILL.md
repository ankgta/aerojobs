---
name: aerojobs-test-and-report
description: Run the full AeroJobs (aerojobs.work) test suite and produce the test report spreadsheet. Covers functional, black-box, end-to-end, phone and cross-browser tests plus security and penetration checks, logging defects, fixing them and re-testing. Use when the owner asks to test the site, after any visible change, or when a bug is reported.
---

# Test AeroJobs and report

Work in the repository **ankgta/aerojobs**. The live site can't be reached from Claude's sandbox, so live
tests run in GitHub Actions; local runs use a site built from the real data.

## What exists

| File | What it does |
| --- | --- |
| `qa/site_tests.py` | Browser tests (Playwright). 36 cases on desktop, plus phone cases, in Chrome, Firefox and Safari's engine. Expected values come from the site's own `/data/jobs-index.json`, so tests work with any data |
| `qa/security_tests.py` | Safe security checks against the live site: HTTPS, headers, exposed files, path tricks, write methods, open redirects, XSS through URL and search, SQL injection, framing. Never floods the site |
| `qa/local_security.py` | Builds the site from hostile job data and checks nothing runs; scans git history for secrets |
| `qa/data_quality.py` | Per-employer data health |
| `qa/build_report.py` | Builds `AeroJobs-Test-Report.xlsx` from two test runs |
| `.github/workflows/qa.yml` | "Test the live website": runs all of the above plus `pip-audit`, saves results to branch `qa-results` (folder `latest/`, one commit per run) |

## Run the tests

1. Make sure the change is deployed: the latest "Update jobs and website" run after your push is green.
2. `gh workflow run qa.yml --repo ankgta/aerojobs --ref main`; wait about 10–11 minutes
   (`gh run list --repo ankgta/aerojobs --workflow qa.yml --limit 1`).
3. Get the results:
   ```bash
   git fetch --depth=20 origin qa-results:refs/remotes/origin/qa-results
   git log --format="%h %s" origin/qa-results          # one commit per run, newest first
   mkdir -p /tmp/qa/latest && git archive origin/qa-results latest | tar -x -C /tmp/qa/latest
   ```
   Files: `results.json` (website), `security.json`, `local_security.json`, `pip-audit.json`, `screens/`.
4. List anything not passing and look at the screenshots of failures. Known and accepted: `TC-JS-01` fails
   in Safari only because of Cloudflare Web Analytics (`/cdn-cgi/rum`), and `SEC-23` (DDoS) is never run.

Faster loop while fixing (local, Chrome only):
```bash
pip install -r requirements.txt -r qa/requirements.txt && python -m playwright install chromium
python -m site_builder.build --out /tmp/site && (cd /tmp/site && python -m http.server 8768 &)
python qa/site_tests.py --base http://localhost:8768 --browsers chromium --out /tmp/qa-local
```
`TC-NAV-05` (404 page) and `TC-JOB-04` (Apply links reach employers) always fail locally; ignore them there.

## When something fails

1. Reproduce it locally if you can, fix the cause, add or extend a test so it can't come back.
2. Add a defect row to the `DEF` list in `qa/build_report.py`: ID, found by, severity, problem, details,
   what was done, status (`Fixed`, `Partly fixed`, `Known issue`, `Owner decision`, `Planned`, `Closed`),
   re-test result. A bug the owner reports is "Owner (black-box test)".
3. Deploy, then re-run the live tests.

## Build the report

`build_report.py` compares the first run of a test round with the latest re-test:

```bash
python qa/build_report.py <first_run>/latest <latest_run>/latest \
  <jobs_before.json> <jobs_after.json> <verify_round1.json> <verify_round2.json> \
  docs/reports/AeroJobs-Test-Report.xlsx
```
- Run folders: `git archive <commit> latest | tar -x -C <dir>` for each `qa-results` commit.
- `jobs_before.json`/`jobs_after.json`: `git show <commit>:data/jobs.json` from the start of the round and now.
- `verify_round*.json`: `git show <commit>:data/verify_report.json` (use the same file twice if there was
  one check). Update the hard-coded employer list (`EMP`) and summary text in the script when they change.
- Then recalculate formulas (the xlsx skill's `recalc.py`) and confirm zero formula errors.

The report has tabs: Summary (with owner decisions), Test cases (result per browser and device), Security
tests, Defects, Employers, Employers not used, Data quality. Commit it to `docs/reports/`, send it to the
owner, and summarise in plain words: what passed, what was fixed, what needs their decision.
