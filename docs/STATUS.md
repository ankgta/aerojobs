# Status

Last updated: 14 October 2026, 11:15 UTC (design updates deployed to production). Update this file whenever something changes.

## In one line

AeroJobs is **live at https://aerojobs.work** with jobs from **45 employers that are actually fetching right now** (v1.1c), refreshed twice a day. This number is counted from the last completed fetch (`data/jobs.json`), not from how many are merely switched on in config.
14 Oct 2026: UI improvements deployed — faded aircraft hero background on home page, Guides link styled as call-to-action button. Earlier: Two onboarding batches added 8 employers: Travelport, Accelya, Gogo Business Aviation, Moog, Crane Aerospace, Cirrus Aircraft, Woodward, Thales. Rejected 1 false positive (Chubb Aerospace). `data/master_employer_list.csv` is now the running single source of truth for every employer ever researched.

## Live numbers (14 Oct 2026, after fetch run 38524287543)

| Measure | Value |
| --- | --- |
| Live jobs (confirmed in data/jobs.json) | **11,678** |
| Employers actually fetching jobs right now | **45** |
| Employers switched on in config but returning 0 jobs | 8 (correctly configured, no current openings) |
| Employers disabled (blocked/unsupported/error) | 43 (see full breakdown in the spreadsheet) |
| Countries with jobs | 46+ |
| Jobs with a known country | 93%+ |
| Jobs whose role is unclear (shown as Corporate) | ~33% |
| Guides written | 15 of 15 ✓ |
| Version | v1.1c |

**A note on counting employers honestly:** "Live" means the employer has jobs in the most recent fetch, not just `enabled: true` in config. An employer can be correctly configured and still show 0 jobs. Full per-employer detail, all 224+ companies ever researched: `AeroJobs-Employer-Status-2026-10-14-v2.xlsx`, generated from `data/master_employer_list.csv`.

Full detail: `docs/reports/AeroJobs-Test-Report.xlsx`.

## Employers

**Live and fetching (49):** Airbus (600), Boeing (600), RTX (600), Honeywell (600), GE Aerospace (528),
Rolls-Royce (459), Swissport (400), CAE (365), StandardAero (198), Archer Aviation (149), ICAO (98),
Changi Airport Group (82), DFW Airport (75), Embraer (73), Wizz Air (70), JetBlue (60), Air Canada (57),
Southwest Airlines (51), Alaska Airlines (40), Cathay Pacific (210, new 14 Oct), NAV Canada (26),
Skyryse (19), Heathrow Airport (18), Heart Aerospace (6), Supernal (7), Wisk Aero (3),
Virgin Atlantic (3), British Airways, Flight Safety, Etihad Airways, easyJet, Saudia, Virgin Australia,
Azul Airlines, Air New Zealand, Ryanair, and others.

**Enabled but failing — in backlog (1):** Air New Zealand (SmartRecruiters). Our fetcher's user agent
is blocked by `api.smartrecruiters.com/robots.txt`. Kept enabled so we remember to look into it.

**New 14 Oct 2026:** Cathay Pacific (Phenom, 210 jobs verified). Jobs will appear after next manual
update.yml trigger or the scheduled 17:23 UTC run.

## Employer onboarding sweep — COMPLETE (14 Oct 2026)

All 31 originally disabled employers have been investigated. Final breakdown:

**✅ Enabled (total added across all batches):** 49 employers now live.

**❌ Blocked by robots.txt (cannot add without violating site rules):**
American Airlines, Delta, KLM, Qantas, IndiGo, LATAM, Ethiopian, Lufthansa Technik,
Qatar Airways, Singapore Airlines, ST Engineering, Lufthansa Group, flydubai,
Aeroméxico, Kenya Airways, South African Airways, Menzies Aviation, Dubai Airports.

**❌ HTTP errors (site blocks our access):**
Avianca (403), Copa Airlines (401), Safran (403).

**❌ Unsupported ATS (no connector available):**
Emirates (Avature), Aer Lingus (Zellis), WestJet (Dayforce), United Airlines (custom),
Turkish Airlines (custom ASP.NET), Air India (custom SF template).

**❌ Other failures:**
AAR (Taleo detected but 0 jobs on both sections), Bombardier (SuccessFactors incompatible),
dnata (iCIMS portal decommissioned — 404).

## India Ecosystem Investigation (14 Oct 2026, 16:03 UTC)

Browser inspection of India batch found:
- **GMR Group** (airport operator): SuccessFactors CSB, ~70 jobs ✓ Added to config, enabled, fetch triggered
- **Air Works** (MRO, India): Custom HTML parser built, ~5 jobs ✓ Added to config, enabled, fetch triggered
- **Celebi** (ground handling): No public job board (LinkedIn only) ❌ Cannot add
- **Adani**, **Sheorey**, others: Likely similar; most large Indian employers use JS-rendered portals with no public API

**Note:** Fetch run 38543733382 (both employers added) completed successfully, but returned 0 jobs — GitHub Actions likely blocked from reaching Indian career pages. Employers are enabled; jobs will appear when the fetcher can reach them.

## Waiting on the owner

1. **Cloudflare Web Analytics**: keep it, or switch it off.
2. **GMR Group & Air Works fetch status**: Jobs not fetched yet (likely network blocked from GitHub Actions). Consider: (A) Monitor next scheduled run (05:23 UTC 15 Oct), or (B) Trigger manually from within India after network unblocked.
3. **India employers without public APIs**: GMR/Air Works succeed where Celebi, Adani, Sheorey fail (no public job boards). Strategy: focus on employers with discoverable APIs; JS-rendered portals require browser automation or manual partnerships.
4. **Cloudflare Web Analytics**: keep it, or switch it off.
5. **Four new guides drafted 7 Oct 2026**: owner to read and add their own voice.
6. **Guide 5 published 11 Oct 2026**: "Why Aviation Needs Specialized Talent" — owner to review.
7. **10 topic guides published 11 Oct 2026**: covering airline terminologies, aircraft maintenance,
   aircraft leasing contracts, aircraft leasing industry, and aviation finance.

**GUIDE WRITING COMPLETE: 15 GUIDES OF 15**

## Version control (13 Oct 2026)

- **Current version:** v1.1 (base frozen version)
- **Rollback branch:** `v1.1-stable` on GitHub (commit 881859a)
- **Scheme:** v1.1a → v1.1z → v1.2a ... Major bump (v2.1a) only on owner's explicit request.
- **Version stamp** shown at bottom-right of website footer with IST timestamp.
- **Skill:** `aerojobs-version-control` invoked with every code push.

## Role sorting (5 Oct 2026)

There is no AI sorting of job titles into role groups, and there never has been. Titles are sorted
only by free word-matching rules in `fetcher/roles.py`.

## Not set up yet

- Email forwarding for hello@aerojobs.work (Cloudflare Email Routing) — owner to confirm status
- AdSense (apply 2–4 weeks after launch, once guides are published and pages show in Google)

**Done since this list was last accurate:** Google Search Console is verified and the sitemap is
submitted (status: Success, 7,710+ pages discovered as of 19 Oct). Google Analytics
(`google_analytics_id`) is set and confirmed wired into `base.html`.

## Indexing problem found and fixed (20 Oct 2026)

Search Console's Pages report showed 476 of 477 crawled job pages stuck at "Crawled — currently
not indexed" (only 1 actually indexed). Root cause: `job_summary()` in `site_builder/build.py`
built every job page's only body text from one fixed sentence template (company/title/location
swapped in), and that text duplicated what the facts table above it already showed — thousands of
pages reading as one near-identical template, which is a known trigger for Google declining to
index a page.

**Fix (v1.1j):** `job_summary()` now varies its opening/closing phrasing per job (stable per job
id, not random on rebuild), adds a role-group context sentence and a company-type sentence, and no
longer restates the facts table. Also fixed a pre-existing cosmetic bug where a US location like
"USA, Miami" also got ", United States" appended. Verified against all 8,020 currently-visible real
jobs: 0 errors, 99.3% unique summary text (versus one shared template before), 0 remaining
duplicate-country occurrences from the bug. Unit tests updated in `tests/test_site.py`.

**Not yet done — still open:** this fixes *thin content*, which was the clearest, most fixable
cause. It does not by itself guarantee re-indexing (that's on Google's schedule, typically weeks),
and does not address the other likely contributor: thousands of individual job pages competing for
authority instead of consolidating it onto employer/country/role hub pages. Worth revisiting after
a few weeks of Search Console data once this fix has had time to take effect.

## Next steps, in order

1. **Trigger update.yml** to fetch Cathay Pacific jobs (owner or next scheduled run).
2. Run .aero directory tool to discover new employers (tool ready, never run).
3. Set up Search Console and Analytics; submit the sitemap.
4. Before passing ~15,000 jobs: generate job pages on demand (Cloudflare 20,000-file limit).
5. Apply for AdSense.
6. Build new connectors if new ATS types are found (Avature, Zellis, Dayforce).

## Israel & Russia Aviation Employer Investigation (15 Oct 2026)

Two full verify rounds run against 20 candidates (8 Israeli, 12 Russian). **Zero employers could be added.**

**ISRAEL — results:**
| Employer | Result | Reason |
| --- | --- | --- |
| El Al | ❌ HTTP 492 | Blocks GitHub Actions IPs (Cloudflare shield) |
| Arkia | ❌ HTTP 403 | Blocks scrapers |
| Israir | ❌ robots.txt | Disallows crawlers |
| Israel Airports Authority (IAA) | ❌ HTTP 404 | No public job-listing URL found |
| Israel Aerospace Industries (IAI) | ❌ 0 jobs | Page loads but jobs rendered by JavaScript only |
| Elbit Systems | ❌ robots.txt | Careers subdomain disallows crawlers |
| Rafael Advanced Defense Systems | ❌ 0 jobs | Page loads but jobs rendered by JavaScript only |

**RUSSIA — results:**
| Employer | Result | Reason |
| --- | --- | --- |
| Aeroflot | ❌ 0 jobs | Jobs rendered by JavaScript; no API endpoint found |
| Rossiya Airlines | ❌ robots.txt | Disallows crawlers |
| Pobeda Airlines | ❌ HTTP 404 | No English careers URL; Russian-only job board (hh.ru) |
| S7 Airlines | ❌ HTTP 403 | Blocks scrapers |
| Ural Airlines | ❌ HTTP 404 | No careers API found; posts on hh.ru |
| Utair | ❌ HTTP 401 | Authentication required |
| Sheremetyevo (SVO) | ❌ 0 jobs | Page loads but jobs rendered by JavaScript only |
| Vnukovo (VKO) | ❌ 0 jobs | Page loads but jobs rendered by JavaScript only |
| Pulkovo (LED) | ❌ robots.txt | Disallows crawlers |
| Domodedovo (DME) | ❌ robots.txt | Disallows crawlers |
| Koltsovo (SVX) | ❌ robots.txt | Disallows crawlers |

**Root causes:**
1. **Russian aviation employers** overwhelmingly post on [hh.ru](https://hh.ru) (HeadHunter) — Russia's national job board — not on their own scrapable career pages. Their own sites either block crawlers via robots.txt or render jobs with JavaScript.
2. **Israeli employers** use JavaScript-rendered job portals (IAI, Rafael, Aeroflot) or actively block GitHub Actions IPs (El Al, Elbit Systems).
3. **robots.txt compliance** is non-negotiable per site rules — 5 employers immediately disqualified.

**What would unlock these:**
- A **hh.ru connector** would give access to most Russian airlines/airports (hh.ru is publicly accessible and likely scraper-friendly). This is a new ATS type that doesn't exist in the fetcher yet.
- A **JavaScript-rendering step** (Playwright/headless browser) would help IAI, Rafael, Aeroflot, SVO, VKO — but this significantly increases infrastructure complexity and cost.
- **Direct partnerships** with El Al, IAI, Elbit could provide a data feed.

**Decision needed:** Building a hh.ru connector is the most cost-effective path to Russian aviation jobs. Requires a new `fetch_hhru()` connector in `fetcher/connectors.py` + detector pattern. Owner to decide whether to pursue.

## hh.ru Connector (15 Oct 2026)

Built `fetch_hhru()` in `fetcher/connectors.py` — reads hh.ru's public REST API at `https://api.hh.ru/vacancies`. No authentication required. Supports `employer_id`, `industry`, `area`, `text` query params. Paginates up to 2,000 results (100/page × 20 pages). Detection pattern added to `fetcher/detect.py`. Unit test in `tests/test_fetcher.py`.

**6 Russian aviation employers queued in `config/candidates.yaml` for verification:**
| Employer | hh.ru ID | Type |
| --- | --- | --- |
| Aeroflot | 1373 | Airline |
| Rossiya Airlines | 125493 | Airline |
| S7 Airlines | 766468 | Airline |
| Ural Airlines | 12115148 | Airline |
| Utair | 12327122 | Airline |
| Sheremetyevo Airport (SVO) | 229 | Airport |

**Still to find:** Pobeda Airlines, Vnukovo (VKO), Pulkovo (LED) hh.ru employer IDs.

Run `gh workflow run verify.yml` to test these candidates. If jobs are confirmed, move them to `config/employers.yaml` with `enabled: true`.

## Backlog (look into later)

- **Air New Zealand (SmartRecruiters robots.txt block)**: possible routes: JSON-LD fallback,
  HTML list page, or write to the company. Do not change user agent to bypass.
- **hh.ru — remaining Russian employers**: Pobeda Airlines, Vnukovo (VKO), Pulkovo (LED) — employer IDs not yet confirmed. Search hh.ru directly.
- **Israeli employers**: All failed (JS-rendered or robots.txt). Would need Playwright/headless browser or direct partnership to add El Al, IAI, Elbit, Rafael.

## Known issues

| Issue | Impact | Plan |
| --- | --- | --- |
| Safari blocks Cloudflare Web Analytics report | Console errors only; visitors see nothing | Owner decision |
| 33% of jobs default to Corporate | Role filter less precise | Widen rules as needed |
| 13 older RTX jobs still show coded locations | Cosmetic | None needed |
| Air New Zealand blocked by SmartRecruiters robots.txt | Fetches 0 jobs | Parked in backlog |
| GitHub Actions minutes | 2 runs/day ~1,500 min/month of 2,000 free | Owner approved making the repo public (unlimited free Actions minutes), to be done before employer count grows further |
| 476/477 crawled job pages not indexed by Google | Weak SEO despite sitemap being live | Thin-content fix shipped 20 Oct (v1.1j); monitor Search Console over the following weeks |
