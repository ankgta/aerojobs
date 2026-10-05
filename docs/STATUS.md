# Status

Last updated: 6 October 2026. Update this file whenever something changes.

## In one line

AeroJobs is **live at https://aerojobs.work** with about **3,600 real jobs** from **10 employers** (soon
**18**), refreshed twice a day. Full testing is done. Eight new employers added 6 Oct; the next scheduled
fetch will pull their jobs.

## Live numbers (5 Oct 2026, 10:55 UTC fetch)

| Measure | Value |
| --- | --- |
| Live jobs | 3,598 |
| Employers switched on | 10 of 57 listed (18 after next fetch) |
| Countries with jobs | 42 |
| Jobs with a known country | 93% |
| Jobs whose role is unclear (shown as Corporate) | 33% |
| Pilot jobs / cabin crew jobs | 7 / 0 |
| Guides written | 3 of about 15 |
| Website test runs passing | 116 of 117 (1 known Safari analytics item) |
| Security tests passing | 28 of 29 (1 not run on purpose: DDoS) |

Full detail: `docs/reports/AeroJobs-Test-Report.xlsx`.

## Employers

**Switched on (18):** Airbus, Boeing, RTX (Collins Aerospace and Pratt & Whitney), GE Aerospace, Rolls-Royce,
Wisk Aero, CAE, NAV Canada (Workday) · Honeywell, Virgin Atlantic, Heathrow Airport, StandardAero, ICAO
(Oracle Recruiting Cloud) · Archer Aviation, Skyryse, Heart Aerospace, Supernal (Greenhouse) · Air New
Zealand (SmartRecruiters). Each capped at 600 jobs while testing.

**New 6 Oct 2026 (8):** Air New Zealand, Heart Aerospace, Supernal (Hyundai eVTOL), StandardAero (MRO),
Wisk Aero, CAE (flight training/simulation), NAV Canada, ICAO. Note: SmartRecruiters API may be blocked
by robots.txt for Air New Zealand — will know after first fetch.

**Blocked by their own rules (robots.txt), so left off:** American Airlines, Delta, KLM, Qantas, IndiGo,
LATAM, Ethiopian, AAR, Lufthansa Technik (careers sites); flydubai, Alaska Airlines (iCIMS); Wizz Air,
Swissport, Menzies, dnata, Etihad (SmartRecruiters).

**Need a new reader first:** JetBlue, Ryanair, Wizz Air (SAP SuccessFactors) · Qatar Airways, easyJet
(Oracle Taleo).

**Hiring system not found yet** (jobs load by script): United, Southwest, Air Canada, Emirates,
British Airways, Lufthansa, Cathay Pacific, Singapore Airlines.

**Not yet explored:** the .aero directory (tool ready, never run) and the rest of the listed employers.

## Waiting on the owner

1. ~~**Honeywell and RTX post many non-aviation jobs**~~ **Resolved 5 Oct 2026**: hard aviation-only filter
   added to `fetcher/roles.py`. Non-aviation titles (building tech, HVAC, fire systems, oil & gas, defence
   weapons) are excluded from all employers. About 61 jobs filtered from the current dataset.
2. **Cloudflare Web Analytics**: keep it, or switch it off if Google Analytics will be used (clears the
   Safari console item).
3. ~~**More airlines**: build SuccessFactors and Taleo readers~~ **In progress 5 Oct 2026**: .aero directory
   discovery workflow triggered to find all available employers.

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
2. Monitor first fetch with 18 employers; disable any that fail or are blocked by robots.txt.
3. Grow airline coverage: SuccessFactors and Taleo readers, then run the .aero directory tool.
4. Write the remaining ~12 guides (skill `aerojobs-write-guides`), owner edits them.
5. Set up Search Console and Analytics; submit the sitemap.
6. Before passing ~15,000 jobs: generate job pages on demand (Cloudflare 20,000-file limit).
7. Apply for AdSense.

## Known issues

| Issue | Impact | Plan |
| --- | --- | --- |
| Safari blocks Cloudflare Web Analytics report | Console errors only; visitors see nothing | Owner decision 2 |
| 33% of jobs default to Corporate | Role filter less precise | Widen rules as needed |
| 13 older RTX jobs still show coded locations | Cosmetic; fixes itself when they update | None needed |
| Few airline jobs | Weak for pilots and cabin crew | Next step 3 |
| SmartRecruiters API may block Air New Zealand | Would need to disable that employer | Check after first fetch |
| GitHub Actions minutes | Private repos get 2,000 free minutes a month. Today's fetch runs took ~25 min each (catching up on 2,000+ job detail pages); at that pace 2 runs a day use ~1,500 min a month | Check run times after a few days. If still long: lower `max_new_details_per_employer`, or make the repository public (unlimited free minutes) |
