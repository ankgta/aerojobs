---
name: aerojobs-add-employers
description: Find, check and switch on employers for the AeroJobs job board (aerojobs.work), or build a reader for a new hiring system (SuccessFactors, Taleo, iCIMS). Use when the owner asks to add a company, get more jobs or airlines, run the .aero directory tool, or fix an employer that stopped working.
---

# Add employers to AeroJobs

Work in the GitHub repository **ankgta/aerojobs** (attach and clone it if it isn't in the session). Read
`docs/STATUS.md` first: it lists which employers are on, blocked, or waiting for a reader.

## Non-negotiable rules

- **Never guess a source.** An employer is switched on only after the checker fetched real jobs from it
  and the sample titles clearly belong to that company.
- **robots.txt wins.** If the checker says robots.txt blocks it, leave the employer off and record it in the
  comment block at the top of `config/employers.yaml`. Never use another address to get around a block.
- Facts only: never add code that stores full job descriptions.

## Step 1: find the hiring system

For each company, find its official careers page (web search), then detect the system:

- Locally (if the sandbox can reach the site): `python -m fetcher.detect <careers page URL>`
- Usually the sandbox can't reach employer sites, so do it on GitHub: put the URLs in
  `config/careers_pages.txt` (one per line), commit, then run the checker (step 2). Its output lands in
  `data/detect_report.txt`.
- For many organisations at once, run the .aero directory tool:
  `gh workflow run discover-aero.yml --repo ankgta/aerojobs --ref main -f check=300`
  (results: `data/aero_directory.csv`, `data/aero_candidates.csv`). Most .aero holders are suppliers or
  associations without job listings; keep only real employers.

Source shapes (copy exactly; `references/hiring-systems.md` has details and pitfalls):

```yaml
source: {ats: workday, url: "https://TENANT.wdN.myworkdayjobs.com/SITE"}
source: {ats: oracle, host: "XXXX.fa.REGION.oraclecloud.com", site: "CX_1"}
source: {ats: greenhouse, board: "boardname"}
source: {ats: lever, company: "name"}            # add region: eu for EU accounts
source: {ats: smartrecruiters, company: "Name"}
source: {ats: jsonld, listing_url: "https://…?page={page}", job_link_pattern: "/job/", max_pages: 5, strip_query: true}
```

## Step 2: check candidates on GitHub

1. Write the candidates to `config/candidates.yaml` (same format as `employers.yaml`, with `source`).
   Several guesses per company are fine (for example `CX_1` and `CX`); the checker shows which works.
2. `git fetch origin main && git rebase FETCH_HEAD`, commit, push.
3. `gh workflow run verify.yml --repo ankgta/aerojobs --ref main`, then wait for it:
   `gh run list --repo ankgta/aerojobs --workflow verify.yml --limit 1` (1–8 minutes).
4. Fetch and read `data/verify_report.json` (`ok`, `jobs_found`, `sample` titles and locations, any
   `error`) and `data/detect_report.txt`.

How to read errors: `robots.txt blocks it` → leave off, record it. HTTP 404 or 422 → wrong address or site
name; find the real one from the careers page's Apply links. HTTP 401/403 → the system refuses outside
readers; leave off. `no jobs` → wrong site or the employer has none open.

## Step 3: switch on

1. In `config/employers.yaml`, set the employer's `source`, `type` (airline, airport, mro, manufacturer,
   ground_services, other), head-office `country` (two letters) and `enabled: true`. Keep the file's
   grouping and comments; update the "Checked … NOT usable" comment block with any blocked sites.
2. Run tests (`python -m pytest -q tests`), commit, rebase, push.
3. A push does **not** fetch jobs. Start a fetch: `gh workflow run update.yml --repo ankgta/aerojobs --ref main`.
   First fetches of big employers take 15–25 minutes.
4. Pull and run `python qa/data_quality.py`. Check the new employer has jobs, most with a country, and a
   sensible role mix. If many locations look like codes or lack a country, improve `fetcher/geo.py`
   (add a test in `tests/test_fetcher.py`).
5. Update `docs/STATUS.md` (employer lists and numbers) and add a line to `docs/HISTORY.md`.
6. Tell the owner in plain words: who was added, how many jobs, who was skipped and why.

## Building a reader for a new hiring system

1. Find the system's public job-list endpoint that its own careers page uses (look at the page's network
   calls or documentation). It must be public, need no login, and be allowed by robots.txt.
2. In `fetcher/connectors.py`, add `fetch_<system>(client, src, max_jobs)` returning raw job dicts
   (`source_id`, `title`, `url`, `location`, `country_code`, `posted_date`, `posted_estimated`,
   `closing_date`, `work_mode`, `employment_type`). Page through results. Never keep descriptions.
   Add an optional `<system>_detail` only if the list lacks country or dates. Register it in `CONNECTORS`.
3. In `fetcher/detect.py`, make the pattern produce a ready `source:` line.
4. Add a test with `FakeClient` in `tests/test_fetcher.py` (see `test_oracle_connector`).
5. Check real employers with step 2, then switch on with step 3.
6. Update the hiring-systems table in `docs/PROJECT.md` and `README.md`.
