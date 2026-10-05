# History

What was done, newest first. For why, see `DECISIONS.md`.

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
