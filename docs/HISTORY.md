# History

What was done, newest first. For why, see `DECISIONS.md`.

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
