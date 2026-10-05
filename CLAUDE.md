# AeroJobs: instructions for Claude

AeroJobs (https://aerojobs.work) is a global job board for aviation. Twice a day a Python fetcher reads
employers' public careers systems, and a Python site builder publishes a static website to Cloudflare Pages.
Everything runs in GitHub Actions; nothing runs on the owner's computer.

Read `docs/STATUS.md` first in every new conversation: it says where things stand, what is waiting on the
owner, and what to do next. `docs/README.md` lists the other docs.

## Working with the owner

- The owner is **not a developer**. Use plain language, no jargon, and say exactly what to click or paste
  when they must do something. Short answers; tables only when comparing things.
- Claude writes code, content and docs. The owner creates accounts, approves decisions, checks results.
- Never ask for or handle passwords, tokens or payments. Keys live only in GitHub Secrets.
- Be honest about limits and costs. Never invent facts about employers, jobs or numbers: check the data.
- Ask before anything hard to undo or that changes what the public sees in a big way (removing employers,
  deleting data, changing the domain, turning on ads). Small fixes and improvements: just do them.

## Rules that protect the site (never break these)

1. **Respect every site's rules.** Obey robots.txt (the fetcher refuses blocked addresses; never work around
   it). Skip LinkedIn, Indeed and any site whose terms forbid automated collection.
2. **Never guess an employer's source.** Only switch an employer on after the checker has fetched real jobs
   from it (skill: `aerojobs-add-employers`).
3. **Store facts only.** Title, location, dates, work mode, employment type. Never store or publish an
   employer's full job description. Job pages use a summary written by our own code.
4. **Every Apply link goes to the employer's own site**, and only `https://`/`http://` links are allowed.
5. **No secrets in the repository.** Tokens go in GitHub Secrets (`CLOUDFLARE_API_TOKEN`,
   `CLOUDFLARE_ACCOUNT_ID`, optional `ANTHROPIC_API_KEY`).

## Where things are

| Path | What it is |
| --- | --- |
| `config/site.yaml` | Site name, domain, contact email, Google IDs, fetcher limits |
| `config/employers.yaml` | Every employer, its hiring-system source, on/off, and notes on blocked sites |
| `config/candidates.yaml`, `config/careers_pages.txt` | Inputs for the employer checker |
| `fetcher/` | Readers per hiring system (`connectors.py`), location and country logic (`geo.py`), role sorting (`roles.py`), the run (`run.py`), checker (`verify.py`), detector (`detect.py`), .aero discovery |
| `site_builder/` | Builds the site from `data/jobs.json`: templates, CSS, JS (live filters in `static/search.js`), hero art |
| `content/` | Guides (`guides/*.md`) and legal pages (`pages/*.md`) |
| `data/` | Job data and run reports, written by the workflows. Don't edit by hand |
| `qa/` | Live-site browser tests, security tests, test report builder |
| `tests/` | Fast code tests, run on every update |
| `docs/` | Project docs: status, decisions, history, runbook, roadmap, reports |
| `.claude/skills/` | Step-by-step procedures for recurring jobs (see below) |

## GitHub workflows (Actions tab)

| Workflow | When | What |
| --- | --- | --- |
| Update jobs and website (`update.yml`) | 05:23 and 17:23 UTC, on push to config/content/site_builder, or by hand | Tests, fetches jobs, saves data, builds and publishes the site, opens an issue if an employer breaks |
| Check candidate employers (`verify.yml`) | By hand | Tests sources in `config/candidates.yaml`, saves `data/verify_report.json` |
| Find employers in the .aero directory (`discover-aero.yml`) | By hand | Lists .aero sites and their careers pages into `data/aero_*.csv` |
| Test the live website (`qa.yml`) | By hand | Browser, phone and security tests against aerojobs.work; results on branch `qa-results` |

## Skills for recurring work

- `aerojobs-operations`: health check, failed runs, alert issues, deploying changes, Dependabot updates.
- `aerojobs-add-employers`: find, check and switch on employers; build a reader for a new hiring system.
- `aerojobs-test-and-report`: run the full test suite and produce the test report spreadsheet.
- `aerojobs-write-guides`: write career guides that help AdSense approval and search traffic.

## How to make a change

1. `git fetch origin main && git rebase FETCH_HEAD` first. **The workflow commits job data to `main` twice
   a day**, so a push without rebasing is often rejected.
2. Install and test: `pip install -r requirements.txt && python -m pytest -q tests` (must pass).
3. To see the site locally: `python -m site_builder.sample && python -m site_builder.build --preview`
   (made-up data), or `python -m site_builder.build` (real data into `public/`).
4. For anything visible on the site, also run the live tests after it deploys (skill: `aerojobs-test-and-report`).
5. Commit with a plain-English message, push to `main`. The push triggers a rebuild and deploy (about 1 minute).
6. Update `docs/STATUS.md` (and `docs/DECISIONS.md` / `docs/HISTORY.md` when relevant) in the same commit.

## Facts that have caused mistakes before

- Pinned versions everywhere (requirements and GitHub Actions by commit ID). Runner pinned to `ubuntu-24.04`.
- Cloudflare free plan: 20,000 files per site. Each job is one page. `max_jobs_per_employer` is 600 while testing.
- The Cloudflare "create project" step only runs when the project is missing; a "project already exists"
  error means that guard broke.
- Safari logs a harmless error from Cloudflare Web Analytics (`/cdn-cgi/rum`). Known, owner to decide.
- Filter counts in `search.js` are recalculated from the other active filters; keep it that way (test TC-FLT-08).
