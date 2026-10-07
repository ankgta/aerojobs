# Status

Last updated: 7 October 2026. Update this file whenever something changes.

## In one line

AeroJobs is **live at https://aerojobs.work** with jobs from **25 employers**, refreshed twice a day.
7 Oct 2026: Breezy HR, iCIMS and Phenom connectors deployed — Southwest Airlines, Alaska Airlines,
Air Canada and Embraer switched on (+221 jobs).

## Live numbers (6 Oct 2026, 05:07 UTC fetch — next fetch will include new employers)

| Measure | Value |
| --- | --- |
| Live jobs | 4,373 |
| Employers switched on | 21 fetching + 1 blocked (Air New Zealand) = 22 enabled, of 65 listed |
| Countries with jobs | 46 |
| Jobs with a known country | 93% |
| Jobs whose role is unclear (shown as Corporate) | 33% |
| Pilot jobs / cabin crew jobs | 7 / 0 |
| Guides written | 7 of about 15 |
| Website test runs passing | 116 of 117 (1 known Safari analytics item) |
| Security tests passing | 28 of 29 (1 not run on purpose: DDoS) |

Full detail: `docs/reports/AeroJobs-Test-Report.xlsx`.

## Employers

**Live and fetching (25):** Airbus (600), Boeing (600), RTX (600), Honeywell (600), GE Aerospace (528),
Rolls-Royce (459), Swissport (400), CAE (365), StandardAero (198), Embraer (73), Archer Aviation (149),
Air Canada (57), ICAO (98), Changi Airport Group (82), Southwest Airlines (51), Wizz Air (70),
JetBlue (60), Alaska Airlines (40), NAV Canada (26), Skyryse (19), Heathrow Airport (18), Supernal (7),
Heart Aerospace (6), Wisk Aero (3), Virgin Atlantic (3).

**Enabled but failing — in backlog (1):** Air New Zealand (SmartRecruiters). Our fetcher's user agent
is blocked by `api.smartrecruiters.com/robots.txt`. Kept enabled so we remember to look into it. See
backlog item below.

**New 6 Oct 2026, batch 1 (7 live + 1 blocked):** Heart Aerospace, Supernal (Hyundai eVTOL),
StandardAero (MRO), Wisk Aero, CAE (flight training/simulation), NAV Canada, ICAO — all fetching jobs.
Air New Zealand enabled but blocked by SmartRecruiters robots.txt (added +775 jobs net: 3,598 → 4,373).

**New 6 Oct 2026, batch 2 (3 live):** JetBlue (60 jobs), Wizz Air (70), Changi Airport Group (82).
SuccessFactors Career Site Builder connector built and deployed; first three employers switched on.

**New 6 Oct 2026, batch 3 (1 live):** Swissport (400 jobs, ground services, Switzerland). Fourth
SuccessFactors employer.

**New 7 Oct 2026, batch 4 (4 live):** Southwest Airlines (51), Alaska Airlines (40), Air Canada (57) —
all via new Phenom/iCIMS connectors. Embraer (73 jobs) — Breezy HR connector. Net ~+221 jobs.

**Blocked by their own rules (robots.txt), so left off:** American Airlines, Delta, KLM, Qantas, IndiGo,
LATAM, Ethiopian, AAR, Lufthansa Technik (careers sites); Etihad (SmartRecruiters API); Qatar Airways,
Menzies Aviation, Singapore Airlines, ST Engineering, Lufthansa Group (Oracle/SF/SR APIs);
flydubai, Ryanair (SuccessFactors).

**SuccessFactors: search page returns 0 jobs (likely JS-rendered):** Bombardier.

**Config needs investigation (returned 0 jobs but no robots.txt block):**
  easyJet (Taleo: section param may be wrong), Saudia (Taleo: same),
  dnata (iCIMS: URL may be wrong), Virgin Australia and DFW Airport (Phenom: sitemaps not found),
  Azul Airlines (Gupy: company_id "voeazul" may be wrong).

**Unsupported ATS (no connector):** Emirates (Avature), British Airways (TalentBrew/Radancy),
Aer Lingus (Zellis), Safran (custom Drupal), WestJet (Dayforce), South African Airways (eRecruit),
Dubai Airports (Cazar),
Aeroméxico (Recruiting.com), Azul (Gupy), Embraer (Breezy HR), United/Singapore Airlines/Cathay Pacific/
Qatar Airways/Turkish Airlines/Saudia/Ethiopian/Kenya Airways/Lufthansa Group/Air India/IndiGo (custom).

**Not yet explored:** the .aero directory (tool ready, never run).

## Waiting on the owner

1. ~~**Honeywell and RTX post many non-aviation jobs**~~ **Resolved 5 Oct 2026**: hard aviation-only filter
   added to `fetcher/roles.py`. Non-aviation titles (building tech, HVAC, fire systems, oil & gas, defence
   weapons) are excluded from all employers. About 61 jobs filtered from the current dataset.
2. **Cloudflare Web Analytics**: keep it, or switch it off if Google Analytics will be used (clears the
   Safari console item).
3. ~~**More airlines**: build SuccessFactors and Taleo readers~~ **SuccessFactors done 6 Oct 2026**: connector
   built and 3 employers live (JetBlue, Wizz Air, Changi Airport). Taleo still needed.
4. **Four new guides drafted 7 Oct 2026** (not yet pushed): commercial pilot in India, cabin crew for
   Gulf airlines, Part-66 B1 vs B2, cadet pilot programmes. Owner to read and add their own voice.

## Role sorting (5 Oct 2026)

There is no AI sorting of job titles into role groups, and there never has been - the option was removed
from the code. Titles are sorted only by free word-matching rules in `fetcher/roles.py` (English, German
and French). A title the rules can't place falls into "Corporate", which was about 33% of jobs on 5 Oct
2026; rules were widened the same day (production/warehouse roles, EHS, more German/French supervisor
terms) to lower that share. If "Corporate" keeps catching jobs that belong elsewhere, send a few example
titles and ask for the rules to be widened again - that's free and has no limit.

Dependabot pull request #4 (Markdown 3.10.3 → 3.11) merged 5 Oct 2026.

## Not set up yet

- Google Search Console and sitemap submission
- Google Analytics (`google_analytics_id` empty)
- Email forwarding for hello@aerojobs.work (Cloudflare Email Routing): owner to confirm it is done
- AdSense (apply 2–4 weeks after launch, once guides are published and pages show in Google)

## Next steps, in order

1. Owner answers the decisions above.
2. Grow airline coverage: SuccessFactors and Taleo readers, then run the .aero directory tool.
3. Write the remaining ~12 guides (skill `aerojobs-write-guides`), owner edits them.
4. Set up Search Console and Analytics; submit the sitemap.
5. Before passing ~15,000 jobs: generate job pages on demand (Cloudflare 20,000-file limit).
6. Apply for AdSense.

## Backlog (look into later)

- **Air New Zealand (SmartRecruiters robots.txt block)**: `api.smartrecruiters.com/robots.txt` disallows
  our user agent. Possible routes: (a) check if their careers page has JSON-LD JobPosting data and use
  the jsonld reader instead; (b) read the SmartRecruiters HTML list page (not the API) if robots.txt
  allows it; (c) write to the company for permission. Do not change the fetcher's user agent to bypass.
  Kept enabled in `config/employers.yaml` so this stays visible.

## Known issues

| Issue | Impact | Plan |
| --- | --- | --- |
| Safari blocks Cloudflare Web Analytics report | Console errors only; visitors see nothing | Owner decision 2 |
| 33% of jobs default to Corporate | Role filter less precise | Widen rules as needed |
| 13 older RTX jobs still show coded locations | Cosmetic; fixes itself when they update | None needed |
| Few airline jobs | Weak for pilots and cabin crew | Next step 3 |
| Air New Zealand blocked by SmartRecruiters robots.txt | Fetches 0 jobs; one error per run in alerts | Parked in backlog above |
| GitHub Actions minutes | Private repos get 2,000 free minutes a month. Today's fetch runs took ~25 min each (catching up on 2,000+ job detail pages); at that pace 2 runs a day use ~1,500 min a month | Check run times after a few days. If still long: lower `max_new_details_per_employer`, or make the repository public (unlimited free minutes) |
