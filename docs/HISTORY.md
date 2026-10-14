# History

What was done, newest first. For why, see `DECISIONS.md`.

## 14 October 2026 (onboarding skill created, batch 2 pushed live)

- **New skill `aerojobs-onboard-and-report`**: a repeatable detect → verify → enable → fetch →
  refresh-spreadsheet pipeline, invoked whenever the owner asks to onboard employers or push ready ones
  live. Replaces one-off ad hoc spreadsheets with `data/master_employer_list.csv` as a running, committed
  single source of truth that each run updates in place.
- **Batch 2 (refined career URLs via web search, not blind guessing)** for large manufacturers, ANSPs
  and business aviation that failed in batch 1's generic guesses. Found real leads for Thales, Pilatus,
  Textron, Woodward.
- **Enabled: Woodward** (Workday, 187 jobs, clean aerospace manufacturing) and **Thales** (Workday, 600
  jobs — a group-wide feed spanning aerospace/defense/security/transport, kept per the owner's existing
  precedent of filtering titles rather than excluding large diversified industrials like Honeywell/RTX).
- **Rejected: Pilatus Aircraft** (SuccessFactors detection was a false positive — the real fetch 404'd)
  and **Textron** (Taleo detected, but a real fetch returned 0 jobs).
- **Fetch confirmed live:** 45 employers, 11,678 jobs (run 38524287543).
- Still unresolved from this pass: Dassault Aviation, Leonardo, Eurocontrol (robots.txt), DFS, ENAIRE,
  Airservices Australia, Airways NZ (HTTP 403), NetJets, Flexjet, Wheels Up, Diehl, Mitsubishi Heavy
  Industries, Kawasaki Heavy Industries — all need browser network inspection to find a real job-feed
  endpoint, if one exists; most are likely JS-rendered with no public API.

## 14 October 2026 (full 224-employer master-list sweep, earlier same day)

- **Reconciled against the original 7 Oct consolidated research list (224 employers).** The owner
  flagged that claimed "live" counts didn't match what the website actually showed — correct: config
  having `enabled: true` is not the same as a real job actually appearing. Going forward, "live" counts
  are read from `data/jobs.json` after a confirmed fetch, not from config state.
- **145 never-before-checked candidates from the master list run through `fetcher.detect`.** 15
  detected a plausible ATS; 6 verified real, aviation-relevant jobs and were enabled: Travelport (19),
  Accelya (10), Gogo Business Aviation (28), Moog (441), Crane Aerospace (307), Cirrus Aircraft (72).
- **Rejected Chubb Aerospace** despite 400 "jobs" detected — samples ("Chubb Life HK", "Underwriter,
  Marine & Specialty") showed this was Chubb's entire global insurance job board, not an
  aerospace-specific feed. Excluded to keep the board aviation-only.
- **Fetch triggered and confirmed:** 43 employers now live with 10,848 real jobs (run 38513999934,
  completed ~06:00 UTC). Full per-employer status (all 224 ever researched) exported to
  `AeroJobs-Employer-Status-Complete-2026-10-14.xlsx` with Status / Reason / Suggested Workaround columns.
- 137 of the 224 have no detectable public hiring system at all (mostly lessors, insurers, consultancies
  and ANSPs — likely LinkedIn/Indeed-only or JS-rendered with no API).

## 14 October 2026 (earlier same day)

- **Cathay Pacific enabled:** Phenom connector, 210 jobs verified. First new employer since Etihad (12 Oct).
- **Full employer onboarding sweep complete:** All 31 originally disabled employers investigated.
  AAR re-tested as Taleo (detected by fetcher.detect) — 0 jobs on both sections, left off.
  Menzies Aviation, ST Engineering, Dubai Airports blocked by robots.txt. Safran HTTP 403.
  Bombardier SuccessFactors incompatible. No further actionable employers remain.
- **Version v1.1 frozen (13 Oct):** Code reviewed, 6 bugs fixed, version stamp added to footer.
  Rollback branch `v1.1-stable` on GitHub. Version control skill created.

## 6 October 2026

- **Swissport enabled (batch 3):** 400 ground-services jobs from Switzerland, the fourth SuccessFactors
  employer. Also researched all ~35 remaining disabled employers: Etihad blocked by SmartRecruiters
  robots.txt, dnata iCIMS returns 404, and the rest use unsupported ATS platforms (Phenom People,
  Avature, TalentBrew, Zellis, Dayforce, custom sites). Updated employers.yaml comment block.
- **SuccessFactors Career Site Builder connector built:** HTML parser for SAP SuccessFactors listing pages.
  Handles standard `/job/<slug>/<id>/` and Changi-style `/<company>/job/<slug>/<id>/` URL patterns with
  pagination. Location cleaner strips repeated title text, job IDs, and dates from messy cell content.
- **8 more employers added (batch 1):** Heart Aerospace, Supernal, StandardAero, Wisk Aero, CAE, NAV Canada,
  ICAO — all fetching. Air New Zealand enabled but blocked by SmartRecruiters robots.txt (+775 jobs net).
- **3 more employers added (batch 2):** JetBlue (60 jobs), Wizz Air (70), Changi Airport Group (82) —
  first SuccessFactors employers live. Total: 20 fetching employers.
- **8 QA test failures fixed:** comma formatting in counts, sub-pixel rounding in CSS.
- **Bombardier and ST Engineering** checked but returned 0 jobs (search pages likely JS-rendered); left off.
  Ryanair SuccessFactors blocked by robots.txt.

## 5 October 2026

- **Project organised for long-term use:** `CLAUDE.md`, structured docs in `docs/`, four skills in
  `.claude/skills/`, test report builder in `qa/`, export package for moving to another Claude account.
- **Filter count bug fixed** (found by the owner): counts now follow the other filters. Test TC-FLT-08 added;
  re-test passed in all 6 browser and device combinations.
- **Full test round on the live site:** 36 website test cases × Chrome, Firefox, Safari engine on desktop
  and phones; 29 security and penetration checks. Report: `docs/reports/AeroJobs-Test-Report.xlsx`.
- **Defects fixed from testing:** Show-more button never hid; phone page widened after filtering; Google job
  data could carry injected markup; 44% of jobs had no country; RTX coded locations; non-English and
  manufacturing roles unsorted.
- **10 real employers switched on** after checking 50 candidates: Airbus, Boeing, RTX, GE Aerospace,
  Rolls-Royce, Honeywell, Virgin Atlantic, Heathrow, Archer Aviation, Skyryse. ~3,600 jobs.
- **New tools:** Oracle Recruiting Cloud reader; multi-page job-page reader; employer checker workflow;
  live-site test workflow.
- **Site went live** at aerojobs.work: GitHub repository created, code pushed, Cloudflare secrets added,
  custom domain active with SSL. GitHub Actions warnings cleared.

## 4 October 2026

- Owner chose a global job board for aviation, AdSense first.
- MVP plan written (`MVP-PLAN.md`).
- MVP built: fetcher (Workday, Greenhouse, Lever, SmartRecruiters, JobPosting readers), site builder,
  About/Contact/Privacy/Terms, 3 guides, setup guide, GitHub workflows.
- Redesign: modern sky-blue look, phone layout, hangar illustration; several rounds of hero layout changes
  requested by the owner (full-width background, aircraft on the right, blinking beacon).
- Security review and fixes; .aero directory discovery tool.
