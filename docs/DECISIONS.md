# Decisions log

Newest first. Add a row whenever the owner decides something or a design choice is made that someone
might later question. "Why" is the part that matters.

| Date | Decision | Why |
| --- | --- | --- |
| 14 Oct 2026 | **No public ATS required to add an employer.** If a career page exists, find a way to fetch it legally — browser inspection for hidden APIs, JSON-LD markup, HTML parsing, custom connectors. Workarounds and monitoring are acceptable; we aim for all aviation employers with public careers pages, not just those with open hiring systems. Only LinkedIn, Indeed, third-party job boards, and sites that explicitly forbid scraping are off-limits. | Owner directive: maximize employer coverage beyond what public APIs alone allow. Career pages are fair game if they're meant for humans to read. |
| 5 Oct 2026 | Filter counts recalculate from the other active filters; choices with 0 jobs are greyed out | Owner found static counts misleading (India showed 225 with Remote ticked) |
| 5 Oct 2026 | Test with 10 real employers and a full test round before growing | Owner's choice: prove the whole system end to end first |
| 5 Oct 2026 | Respect robots.txt even when it blocks major airlines | Legal and reputational safety; also a project rule from day one |
| 5 Oct 2026 | Cap 600 jobs per employer, 150 new job detail pages per employer per run | Keep runs short and stay well under Cloudflare's 20,000-file limit while testing |
| 5 Oct 2026 | Add an Oracle Recruiting Cloud reader | Virgin Atlantic, Heathrow and Honeywell use it; found while checking employers |
| 5 Oct 2026 | Country detection uses company location codes and the GeoNames town list | 44% of real jobs had no country; now 93% do |
| 5 Oct 2026 | Pin GitHub Actions to Node 24 versions by commit ID; run on `ubuntu-24.04` | Clear GitHub's deprecation warnings; avoid surprise changes from upgrades |
| 5 Oct 2026 | Site name AeroJobs, domain aerojobs.work, private GitHub repo ankgta/aerojobs | Owner's choice |
| 4 Oct 2026 | Use https://information.aero/directory as the main source for finding employers | Owner's suggestion; lists .aero holders by category |
| 4 Oct 2026 | Security fixes before launch: only http(s) Apply links, security headers, pinned versions, Dependabot | Close the gaps found in the security review |
| 4 Oct 2026 | Hero banner is an original illustration (double-deck jet in a hangar), used as a full-width background with the aircraft on the right | Owner's design direction; original art avoids licence and airline-branding problems |
| 4 Oct 2026 | No database for the MVP: job data is a JSON file saved in GitHub | Fewer accounts and moving parts; Supabase free projects pause after 7 days. A database returns with job alert emails |
| 4 Oct 2026 | Build the site with a small Python program (Jinja templates), not Next.js | Fewer parts to break, builds in seconds, same visitor experience |
| 4 Oct 2026 | Host on Cloudflare (Pages + domain), not Vercel | Vercel's free plan forbids commercial use, including ads |
| 4 Oct 2026 | Fetch every 12 hours | Employers post over days; hourly adds cost and load for no benefit |
| 4 Oct 2026 | Store facts only and write our own short summaries; link to the employer to apply | Respect employers' content; AdSense rejects copied content |
| 4 Oct 2026 | First income: Google AdSense; original guides needed before applying | Low effort to run; AdSense needs original content |
| 4 Oct 2026 | Global scope from day one, English-language careers pages first | Aviation careers are international; English covers most large employers |
