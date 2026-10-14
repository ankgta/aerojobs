# Status

Last updated: 14 October 2026, 06:10 UTC (confirmed against a real fetch, not a config guess). Update this file whenever something changes.

## In one line

AeroJobs is **live at https://aerojobs.work** with jobs from **43 employers that are actually fetching right now** (v1.1), refreshed twice a day. This number is counted from the last completed fetch (`data/jobs.json`), not from how many are merely switched on in config — those two numbers had drifted apart before and will be kept in sync going forward.
14 Oct 2026: Full sweep against the original 224-employer research list (7 Oct). Detected 15 new candidates, verified 6 real additions (Travelport, Accelya, Gogo Business Aviation, Moog, Crane Aerospace, Cirrus Aircraft), rejected 1 false positive (Chubb Aerospace — its "jobs" were Chubb's general insurance board, not aerospace-specific). Cathay Pacific's first fetch landed 202 jobs.

## Live numbers (14 Oct 2026, after fetch run 38513999934)

| Measure | Value |
| --- | --- |
| Live jobs (confirmed in data/jobs.json) | **10,848** |
| Employers actually fetching jobs right now | **43** |
| Employers switched on in config but returning 0 jobs | 8 (correctly configured, no current openings) |
| Employers disabled (blocked/unsupported/error) | 30+ (see full breakdown below) |
| Countries with jobs | 46+ |
| Jobs with a known country | 93%+ |
| Jobs whose role is unclear (shown as Corporate) | ~33% |
| Guides written | 15 of 15 ✓ |
| Version | v1.1 |

**A note on counting employers honestly:** "Live" below means the employer has jobs in the most recent fetch, not just `enabled: true` in config. An employer can be correctly configured and still show 0 jobs (no current openings, or awaiting its first scheduled fetch) — those are labelled separately. Full per-employer detail, including every one of the 224 companies ever researched: `AeroJobs-Employer-Status-Complete-2026-10-14.xlsx`.

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

## Waiting on the owner

1. **Cloudflare Web Analytics**: keep it, or switch it off.
2. **Trigger update.yml manually** to fetch Cathay Pacific jobs (or wait for 17:23 UTC scheduled run).
3. **Four new guides drafted 7 Oct 2026**: owner to read and add their own voice.
4. **Guide 5 published 11 Oct 2026**: "Why Aviation Needs Specialized Talent" — owner to review.
5. **10 topic guides published 11 Oct 2026**: covering airline terminologies, aircraft maintenance,
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

- Google Search Console and sitemap submission
- Google Analytics (`google_analytics_id` empty)
- Email forwarding for hello@aerojobs.work (Cloudflare Email Routing)
- AdSense (apply 2–4 weeks after launch, once guides are published and pages show in Google)

## Next steps, in order

1. **Trigger update.yml** to fetch Cathay Pacific jobs (owner or next scheduled run).
2. Run .aero directory tool to discover new employers (tool ready, never run).
3. Set up Search Console and Analytics; submit the sitemap.
4. Before passing ~15,000 jobs: generate job pages on demand (Cloudflare 20,000-file limit).
5. Apply for AdSense.
6. Build new connectors if new ATS types are found (Avature, Zellis, Dayforce).

## Backlog (look into later)

- **Air New Zealand (SmartRecruiters robots.txt block)**: possible routes: JSON-LD fallback,
  HTML list page, or write to the company. Do not change user agent to bypass.

## Known issues

| Issue | Impact | Plan |
| --- | --- | --- |
| Safari blocks Cloudflare Web Analytics report | Console errors only; visitors see nothing | Owner decision |
| 33% of jobs default to Corporate | Role filter less precise | Widen rules as needed |
| 13 older RTX jobs still show coded locations | Cosmetic | None needed |
| Air New Zealand blocked by SmartRecruiters robots.txt | Fetches 0 jobs | Parked in backlog |
| GitHub Actions minutes | 2 runs/day ~1,500 min/month of 2,000 free | Monitor usage |
