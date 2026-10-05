# AeroJobs: project overview

## What it is

A global job website for one niche: aviation and the airline industry. It collects open jobs from the
careers sites of airlines, airports, maintenance (MRO) companies, manufacturers and .aero organisations,
and shows them in one place with filters. Visitors apply on the employer's own site. Website first; a phone
app comes later, only if users ask for it.

## Identity and accounts

| Thing | Value |
| --- | --- |
| Site name | AeroJobs |
| Address | https://aerojobs.work and https://www.aerojobs.work (also aerojobs.pages.dev) |
| Contact shown on site | hello@aerojobs.work (Cloudflare Email Routing → site Gmail) |
| Code | GitHub, private repository **ankgta/aerojobs**, branch `main` |
| Hosting and domain | Cloudflare (Pages project `aerojobs`, domain registered at Cloudflare) |
| GitHub secrets | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (optional later: `ANTHROPIC_API_KEY`) |
| Owner accounts | Site Gmail, GitHub, Cloudflare. Later: Google Search Console, Analytics, AdSense |

The owner holds every password. Claude never sees or stores them.

## How it works

```
Employer careers systems ─► Job fetcher ─► data/jobs.json ─► Site builder ─► Cloudflare Pages
(Workday, Oracle, Greenhouse…)  (Python)      (in GitHub)      (Python)       (aerojobs.work)
```

All of it runs in GitHub Actions at 05:23 and 17:23 UTC.

1. **Fetcher** (`fetcher/run.py`) reads each switched-on employer in `config/employers.yaml` through the
   reader for its hiring system, pausing 1.5 s between requests and obeying robots.txt.
2. It keeps only facts: title, location, country, dates, work mode, employment type. Coded company
   locations become "City, Country". Country is found from location text, company codes and a world town
   list (GeoNames). Role is sorted by keyword rules (several languages), optionally by AI for unclear titles.
3. Jobs missing from two runs in a row are hidden; hidden jobs are deleted after 30 days.
4. If an employer errors or returns zero jobs, GitHub opens an issue "Job fetcher needs attention", which
   emails the owner.
5. **Site builder** (`site_builder/build.py`) makes: home page with search and live filters, one page per
   job (with Google for Jobs data), employer, country and role pages, guides, legal pages, sitemap,
   robots.txt, security headers (`_headers`), and a home-screen manifest.

## Hiring systems we can read

| System | Reader | Used by (switched on) |
| --- | --- | --- |
| Workday | `workday` | Airbus, Boeing, RTX, GE Aerospace, Rolls-Royce |
| Oracle Recruiting Cloud | `oracle` | Honeywell, Virgin Atlantic, Heathrow |
| Greenhouse | `greenhouse` | Archer Aviation, Skyryse |
| Lever | `lever` | (none yet) |
| SmartRecruiters | `smartrecruiters` | (none; its API is blocked by robots.txt for the airlines tried) |
| Google JobPosting data in pages | `jsonld` (with multi-page listings) | (none yet) |
| SAP SuccessFactors, Oracle Taleo, iCIMS | detected only | Readers not built yet |

`python -m fetcher.detect <careers page>` tells which system a careers page uses.

## Where new employers come from

1. **The .aero directory, https://information.aero/directory**: lists .aero domain holders in 19
   categories (airlines, airports, aerospace, air freight, MRO suppliers, training, air navigation and more).
   Tool: `python -m fetcher.discover_aero --check N` or the workflow "Find employers in the .aero
   directory". It reads only the public listing pages (`/taxonomy/term/all?page=N`; robots.txt blocks
   `/search/`), stores names and addresses only, never descriptions.
2. The list of large employers in `config/employers.yaml` (most big airlines use .com addresses).

## The website

- Filters: keyword, country (grouped by region), job role (8 groups), work mode, posted date (24 h, 48 h,
  week, month, older), employer type. Every count updates live from the other filters; empty choices are
  greyed out. Sort: newest first or closing soonest. Shareable links keep the filters.
- Role groups: Pilots; Cabin crew; Aircraft engineering and maintenance (MRO); Ground operations and airport
  services; Air traffic and flight operations; Cargo and logistics; Customer service and sales; Corporate.
- Design: sky-blue theme, Sora and Figtree fonts, original hangar illustration of a double-deck jet with a
  blinking red beacon, job cards with New and Closes soon tags. Phone layout with a bottom-sheet filter
  panel, sticky results bar and sticky Apply button. Works in Chrome, Firefox and Safari.
- Content: About, Contact, Privacy (mentions Google ads and cookies), Terms, 3 guides.
- Security: static files only (no database, forms or logins), HTTPS with HSTS, content security policy,
  no framing by other sites, unsafe links rejected, job text escaped, pinned software, Dependabot.

## Money

Running cost: the domain (about $10–15 a year). Optional AI sorting: up to $5 a month.

Income plan: Google AdSense first. Later, in order: job-board partner feeds (Adzuna, Jooble), job alert
emails with sponsor slots, affiliate links (pilot training, cabin crew courses, exam prep, CV services,
pilot gear), paid featured jobs via a Stripe payment link.

## Limits to remember

- Cloudflare Pages free plan: 20,000 files per site (about 19,000 jobs at one page each).
- GitHub private repository: 2,000 free Actions minutes a month. A fetch run takes up to ~25 minutes for
  large employers; watch usage as employers grow.
- Job descriptions are deliberately short summaries, so Google for Jobs may show some jobs less.
