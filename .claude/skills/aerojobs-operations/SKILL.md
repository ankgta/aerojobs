---
name: aerojobs-operations
description: Day-to-day running of the AeroJobs job board (aerojobs.work) - health checks, failed GitHub Actions runs, "Job fetcher needs attention" alert issues, deploying a change safely, Dependabot updates and Actions minutes. Use when the owner asks whether things are working, pastes an error, reports something broken, or asks for any code or settings change to be shipped.
---

# Run AeroJobs day to day

Work in **ankgta/aerojobs** (attach and clone if needed). Start with `docs/STATUS.md`. Explain everything
to the owner in plain words; they are not a developer.

## Health check (when asked "is everything OK?")

```bash
gh run list --repo ankgta/aerojobs --limit 10                 # newest runs and results
gh api repos/ankgta/aerojobs/issues --jq '.[] | "#\(.number) \(.title)"'   # open alerts and PRs
git fetch origin main && git rebase FETCH_HEAD && python qa/data_quality.py
```
Healthy means: the latest "Update jobs and website" is green and under 13 hours old (schedule 05:23 and
17:23 UTC), no open "Job fetcher needs attention" issue, every switched-on employer has jobs, and no
employer's count dropped sharply. The sandbox usually can't open aerojobs.work; if a live check is needed,
run the live tests (skill `aerojobs-test-and-report`) or ask the owner to look.

Report back in three lines: working or not, numbers (jobs, employers), anything needing their decision.

## A "Job fetcher needs attention" issue

The issue lists employers that errored, returned zero jobs, or dropped by over 80%. Other employers kept
updating. For each:
- `robots.txt does not allow` → the employer changed its rules. Switch it off (`enabled: false`), record it.
- HTTP 404/410/422 → the careers address changed. Re-detect and re-check (skill `aerojobs-add-employers`).
- HTTP 429/5xx or timeouts once → temporary; check the next run before acting.
- Zero jobs → open the employer's careers page with web search; if jobs exist, the source changed.
Comment on the issue with what was done, close it when fixed (`gh api -X PATCH repos/ankgta/aerojobs/issues/N -f state=closed`).

## A failed run

`gh run view <id> --repo ankgta/aerojobs --log-failed` and read the first real error.

| Error | Cause and fix |
| --- | --- |
| Tests failed in "Check the code still works" | A code change broke something; fix and add a test |
| Push rejected in "Save job data" | Two runs overlapped; the next run catches up. Persistent: check the `concurrency` block |
| "A project with this name already exists" | The create-if-missing guard in `update.yml` broke |
| Cloudflare 401/403 when publishing | Token expired or lost the Cloudflare Pages Edit permission; owner makes a new one (`docs/RUNBOOK.md`) |
| "Permission denied" pushing data | Repo Settings → Actions → General → Workflow permissions → Read and write |
| Run cancelled at the time limit | An employer is very slow; lower `max_new_details_per_employer` in `config/site.yaml` |

## Shipping any change

1. `git fetch origin main && git rebase FETCH_HEAD` (the workflow commits data to `main` twice a day).
2. Make the change; `python -m pytest -q tests` must pass. For visible changes, check locally
   (`python -m site_builder.build --out /tmp/site` and serve it) and take a screenshot.
3. Commit with a plain-English message, rebase again, push. A push to `config/`, `content/` or
   `site_builder/` rebuilds and deploys in about a minute (it does not fetch new jobs).
4. Wait for the green run. For visible changes, run the live tests.
5. Update `docs/STATUS.md`; add to `docs/DECISIONS.md` and `docs/HISTORY.md` when relevant.

## Dependabot pull requests

Dependabot opens weekly PRs for package and Action updates. Check the PR's checks passed
(`gh api repos/ankgta/aerojobs/commits/<head sha>/check-runs --jq '.check_runs[] | "\(.name) \(.conclusion)"'`),
read what changed, then merge: `gh api -X PUT repos/ankgta/aerojobs/pulls/N/merge -f merge_method=squash`.
Major-version updates of Playwright, Jinja2 or the Cloudflare action: run the full tests after merging.

## GitHub Actions minutes

The repository is private: 2,000 free minutes a month. Check usage:
`gh api "repos/ankgta/aerojobs/actions/runs?per_page=60" --jq '.workflow_runs[] | "\(.name) \(.run_started_at) \(.updated_at)"'`.
If fetch runs stay long, lower `max_new_details_per_employer` or suggest making the repository public
(unlimited free minutes; code and job data become visible, which is harmless here). The owner decides.

## Never

- Never put tokens, passwords or keys in the repository or in chat.
- Never disable the robots.txt check, raise request speed, or bypass a block.
- Never force-push `main` or delete job data by hand.
