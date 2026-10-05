# Aviation Jobs Portal

A global job board for the aviation industry. Twice a day it reads the careers sites of airlines, airports, maintenance companies and aerospace manufacturers, and publishes every open job on one searchable website.

To get it live, follow **SETUP-GUIDE.md**. This file explains how it works.

## How it works

```
 Employer careers sites ──► Job fetcher ──► data/jobs.json ──► Website builder ──► Cloudflare Pages
 (Workday, Greenhouse...)   (Python)        (saved on GitHub)   (Python)            (your live site)
```

GitHub runs all of this automatically at 05:23 and 17:23 UTC every day. Nothing runs on your computer.

1. **The fetcher** (`fetcher/`) reads each switched-on employer in `config/employers.yaml`. It pauses between requests, obeys each site's robots.txt rules, and keeps only the facts (title, location, dates, work mode). It never stores the employer's full job description.
2. Jobs missing from **two runs in a row** are hidden. Expired jobs are deleted after 30 days.
3. If an employer returns zero jobs or an error, GitHub opens an **issue** titled "Job fetcher needs attention", which GitHub emails to you.
4. **The website builder** (`site_builder/`) turns the job data into a fast website: search with filters, one page per job (with Google for Jobs data), pages for each employer, country and role, guides, and the legal pages AdSense needs.

## What is where

| Folder or file | What it holds | Who edits it |
| --- | --- | --- |
| `config/site.yaml` | Site name, domain, contact email, AdSense and Analytics IDs | You |
| `config/employers.yaml` | The employers to read, and how | Claude, you approve |
| `content/guides/` | Guide articles, one file each | You and Claude |
| `content/pages/` | About, Contact, Privacy policy, Terms | You and Claude |
| `data/` | Job data, saved automatically. Don't edit by hand. | The fetcher |
| `fetcher/` `site_builder/` `tests/` | The code | Claude |

## Two changes from the original plan, and why

- **No separate database.** The job data is a file saved in your GitHub project after each run. For thousands of jobs this is plenty, and it removes the Supabase account and its "pauses after 7 days" problem. A database comes back when we add job alert emails.
- **Simpler website tool.** The site is built by a short Python program instead of Next.js. Both produce the same kind of website, but this one has fewer parts to break and builds in seconds.

## Finding more employers: the .aero directory

The [.aero directory at information.aero](https://information.aero/directory) lists organisations that hold a .aero web address (airlines, airports, aerospace, MRO, air freight, training and more). It is our main source for growing the employer list.

1. In GitHub, open **Actions**, then **Find employers in the .aero directory**, then **Run workflow**.
2. It reads the directory's public listing pages (never its search pages, which its robots.txt blocks), then checks each organisation's home page for a careers link and works out which hiring system it uses.
3. Two lists are saved: `data/aero_directory.csv` (every .aero website found) and `data/aero_candidates.csv` (careers page, hiring system and a ready-made config line where possible).
4. Claude reviews the candidates with you and adds the real employers to `config/employers.yaml`. Nothing is switched on automatically, and only names and web addresses are kept.

## Design and phones

- Works in Chrome, Safari and Firefox on iPhone, Android and desktop. Tested in Chrome at phone widths from 320px to 412px, tablet and desktop. Safari and Firefox use the same standard features, with fallbacks where Safari needs them.
- On phones: filters open as a panel from the bottom of the screen, the results bar stays at the top while you scroll, job pages have an Apply button fixed at the bottom, and visitors can add the site to their home screen like an app.
- The banner illustration is `site_builder/static/hero-hangar.svg`, drawn by `site_builder/art/make_hero.py`. To use a photo instead, add it to `site_builder/static/` and set `hero_image` in `config/site.yaml` (for example `static/hero.jpg`). Only use a photo you have the right to use commercially.

## Hiring systems supported

| System | Status |
| --- | --- |
| Workday | Supported (many large airlines and manufacturers) |
| Greenhouse, Lever, SmartRecruiters | Supported |
| Google JobPosting data in web pages | Supported |
| SAP SuccessFactors, Oracle Taleo, iCIMS, Oracle Cloud | Detected but not read yet. Next connectors to build. |

To find out which system an employer uses, run `python -m fetcher.detect <careers page link>`.

## Known limits

- **Employer list not verified yet.** All 55 starting employers are listed but switched off. Each needs its careers system checked before it is switched on. This is the next task.
- **Short descriptions on job pages.** Google for Jobs prefers full descriptions. We deliberately show short summaries to respect employers' content, so some jobs may get less visibility there.
- **Some sites block automated reading.** When a site's robots.txt disallows it, the fetcher skips it and reports it rather than working around it.

## Commands (for Claude, or if you are curious)

```
pip install -r requirements.txt
python -m pytest -q tests              # check everything works
python -m fetcher.run                  # fetch jobs
python -m fetcher.run --only boeing    # fetch one employer
python -m site_builder.build           # build the live site into public/
python -m site_builder.sample && python -m site_builder.build --preview   # preview with made-up data
```
