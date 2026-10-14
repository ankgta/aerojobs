---
name: aerojobs-onboard-and-report
description: Run a full employer-onboarding pass for AeroJobs (aerojobs.work) against the master candidate list - detect, verify, enable what's real, push it live, and refresh the employer status spreadsheet. Use when the owner says to onboard employers, push ready ones live, "get them live", or asks for an updated status/reason/workaround spreadsheet.
---

# Onboard employers and report status (AeroJobs)

A repeatable pipeline that takes the project's running master candidate list, finds which ones can
actually go live, pushes only the ones proven to work, and leaves behind a spreadsheet the owner can
read without any jargon. Run this whenever the owner asks to onboard employers, "push what's ready",
or wants the status sheet refreshed.

This skill assumes `aerojobs-add-employers`'s non-negotiable rules: never guess a source, robots.txt
wins, facts only (no stored job descriptions), and an employer goes live only after the checker fetches
real jobs that are plausibly that company's.

## Where the master list lives

The running master list of every employer ever researched (224 as of 14 Oct 2026, growing) lives as
`data/master_employer_list.csv` in the repo. **Always read and update this file** — it is the single
source of truth this skill works from, not a one-off spreadsheet in chat history. If it doesn't exist
yet, create it with the columns below from whatever list the owner last shared, and commit it so future
runs have it.

Columns: `Name, Category, Country, Status, ATS, Jobs, Reason, Workaround, Last Checked`

`Status` is one of: `LIVE`, `ENABLED (0 jobs)`, `CANDIDATE (detected, unverified)`,
`CANDIDATE (no system found)`, `BLOCKED (robots.txt)`, `DISABLED (unsupported ATS)`,
`DISABLED (site error)`, `DISABLED (needs URL fix)`, `REJECTED`.

## Step 1: pick the batch to work

Filter the master list for rows not already `LIVE` or a terminal `BLOCKED`/`DISABLED`/`REJECTED` status.
Group by what's needed:

- **`CANDIDATE (detected, unverified)`** — a source is already guessed; just needs `verify.yml`. Go to
  Step 3 directly.
- **`CANDIDATE (no system found)` or no `Status` yet** — needs detection first. Go to Step 2.
- A **reason worth retrying** (e.g. "HTTP error, 24h retry window", a guessed URL that previously 404'd) —
  worth one more pass if circumstances may have changed. Otherwise leave terminal statuses alone; don't
  re-run detection against a confirmed robots.txt block every time this skill fires.

Work in batches of 30–50 careers-page URLs per detection run (bigger batches make `verify.yml` take much
longer and don't parallelise — GitHub Actions runs it as one sequential job).

## Step 2: detect

For each candidate needing a URL, find its real current careers page (web search if not already known —
don't guess domains blind; a wrong guess just wastes a detection cycle). Append the URLs to
`config/careers_pages.txt` under a dated batch comment, commit, push, then:

```bash
gh workflow run verify.yml --repo ankgta/aerojobs --ref main
```

Poll with `gh run list --repo ankgta/aerojobs --workflow verify.yml --limit 1 --json status,conclusion`
every few minutes (detection on ~150 URLs takes roughly 10–15 minutes; scale with batch size). When
`status` is `completed`, `git fetch && git rebase` to pull `data/detect_report.txt`.

Read the report. For each `source: {...}` suggestion:
- **Reject generic/widget false positives on sight**: a bare `https://www.icims.com` (not a
  `careers-<company>.icims.com` subdomain), a Greenhouse board named something generic like `embed`, or
  an ATS/URL mismatch (e.g. a "cornerstone" result pointing at an `ashbyhq.com` URL). These come from
  cookie-consent scripts or tracking pixels on the page, not a real job feed. Mark the candidate
  `CANDIDATE (no system found)` and move on — don't waste a verify cycle on it.
- **Keep everything else as a real lead.**

## Step 3: verify

Write real leads into `config/candidates.yaml` (the standard shape — see `aerojobs-add-employers`), commit,
push, then:

```bash
gh workflow run verify.yml --repo ankgta/aerojobs --ref main
```

Poll the same way. Pull `data/verify_report.json` when done.

For each result:
- `ok: false` → record why (`error` field) in the master list's `Reason`/`Workaround` columns using the
  same categories `aerojobs-add-employers` uses (robots.txt, HTTP error, wrong site/section, no jobs).
- `ok: true` with `jobs_found > 0` → **read the `sample` titles and locations before celebrating.**
  This is the step that catches false positives like "Chubb Aerospace" turning out to be a general
  insurer's entire global job board. Ask: do these titles plausibly belong to this company's aviation/
  aerospace work? If a sample reads like an unrelated division or a totally different business line,
  reject it — mark `REJECTED` with the reason, don't enable it just because the connector worked.
- `ok: true`, real jobs, titles check out → **this one is ready to go live.**

## Step 4: push the ready ones live

For every candidate that passed Step 3:

1. Add it to `config/employers.yaml` with `enabled: true`, the verified `source`, correct `type` and
   head-office `country`. Keep the file's existing grouping/comment style — add a dated comment block
   noting what was added and why (and what was rejected and why, so the next run doesn't repeat the work).
2. Clear the entries out of `config/candidates.yaml` (set back to `employers: []` or remove just the
   resolved ones).
3. `python -m pytest -q tests` if the sandbox has network access to install dependencies; otherwise rely
   on GitHub's own test step in `update.yml`.
4. Commit and push. **Then invoke `aerojobs-version-control`** before or alongside this commit — every
   push gets a version bump, this one included.
5. Push does not fetch jobs by itself. Trigger the real fetch so the website actually reflects the new
   employers, not just the config:
   ```bash
   gh workflow run update.yml --repo ankgta/aerojobs --ref main
   ```
   Poll until `completed` (15–25 minutes for a big batch). Pull `data/jobs.json` afterward.

## Step 5: refresh the spreadsheet and the master list

**Count "live" from `data/jobs.json` after the fetch completes, never from `enabled: true` in config.**
An employer can be enabled and still show 0 jobs (no current openings, or awaiting its first scheduled
run) — that is a different, honest status, not "live". This distinction is the exact mistake that
prompted this skill to exist; don't repeat it.

1. Update `data/master_employer_list.csv` in place: set `Status`, `Jobs`, `Reason`, `Workaround`, and
   `Last Checked` (today's date) for every row touched this run. Commit it — this file is the running
   memory of the whole onboarding effort, not a disposable scratch file.
2. Rebuild the owner-facing spreadsheet from that CSV: one row per employer ever researched, colour-coded
   by status (green = LIVE, yellow = ENABLED but 0 jobs or unverified candidate, grey = no system found,
   red = blocked/disabled, purple = rejected), with `Reason` and `Suggested Workaround` columns in plain
   language — the owner is not a developer. Include a Summary sheet with counts per status and the total
   live job count. Name it `AeroJobs-Employer-Status-<date>.xlsx` and send it to the owner.
3. Update `docs/STATUS.md`'s live-numbers table and `docs/HISTORY.md` with a dated entry: what was
   added, what was rejected and why, what remains uncheckable. Commit alongside the spreadsheet.

## Step 6: tell the owner, plainly

No jargon. Say: how many went live this run, their names and job counts, the one or two most interesting
rejections (and why), and how many candidates remain genuinely unresolved (not just "pending" — say
whether they need a browser inspection, a different URL, or are simply not fetchable). Mention the
spreadsheet file and that the website has already been refreshed to match it — don't make the owner ask
"does the site actually show this yet?"

## Guardrails (same as aerojobs-add-employers, restated because they matter most here)

- Never switch an employer on without a verify.yml run that actually returned real, on-topic job samples.
- robots.txt blocks are permanent until the owner says otherwise. Never retry-bypass them.
- Never store full job descriptions — titles, locations, dates, work mode, employment type only.
- This project's instructions require the owner's permission before committing/pushing changes to the
  live site or its connectors. If this skill is invoked ambiently rather than in direct response to the
  owner asking for this exact onboarding run, confirm before pushing — not before researching or
  detecting, which are read-only.
