# Hiring systems: what we learned

Checked 5 October 2026. Re-check before relying on anything here.

## Workday (reader: `workday`)
- Careers sites look like `https://TENANT.wdN.myworkdayjobs.com/en-US/SITE`. The source URL drops the
  language part: `https://TENANT.wdN.myworkdayjobs.com/SITE`.
- The reader posts to `/wday/cxs/TENANT/SITE/jobs` 20 jobs at a time. Workday reports the total only on
  the first page.
- Guessed site names usually fail with HTTP 422 (Bombardier, Spirit, Textron, Embraer, AAR, Alaska,
  Air Canada, Heathrow, JetBlue, Virgin Atlantic all failed on guesses). Take the real site name from
  the employer's Apply links.
- "Posted 30+ Days Ago" is an estimate. Exact dates, country, closing date and work mode come from the job
  detail call, which the fetcher makes for up to `max_new_details_per_employer` new jobs per run.
- Working: Airbus `ag.wd3/Airbus`, Boeing `boeing.wd1/EXTERNAL_CAREERS`, RTX
  `globalhr.wd5/REC_RTX_Ext_Gateway`, GE Aerospace `geaerospace.wd5/GE_ExternalSite`, Rolls-Royce
  `rollsroyce.wd3/professional`.

## Oracle Recruiting Cloud (reader: `oracle`)
- Careers pages link to `https://XXXX.fa.REGION.oraclecloud.com/hcmUI/CandidateExperience/en/sites/SITE`.
- The reader calls `/hcmRestApi/resources/latest/recruitingCEJobRequisitions` with `siteNumber=SITE`,
  25 at a time. Gives country, dates and workplace type directly (no detail calls).
- Several site numbers can show the same jobs (`CX_1`, `CX`, `CX_3001`); use the one on the careers page.
- Working: Honeywell `ibqbjb.fa.ocs` `CX_1`, Virgin Atlantic `iagime.fa.ocs` `CX_1`, Heathrow
  `encd.fa.em3` `CX_3001`.

## Greenhouse (`greenhouse`), Lever (`lever`)
- Public JSON boards: `boards-api.greenhouse.io/v1/boards/BOARD/jobs`, `api.lever.co/v0/postings/COMPANY`.
- Board names are often not the company name (Archer is `archer56`). Guesses for Joby, Wisk, Boom,
  Hermeus, BETA, Reliable Robotics, Blade, JSX, Wheels Up, Surf Air, Merlin, Electra, ZeroAvia, Skyports
  and Vertical returned 404: find the real board from their Apply links.
- Working: Archer Aviation `archer56`, Skyryse `skyryse`.

## SmartRecruiters (`smartrecruiters`)
- The public API `api.smartrecruiters.com/v1/companies/X/postings` is **disallowed by robots.txt**.
  Wizz Air, Swissport, Menzies, dnata, Etihad and SmartLynx all failed for that reason. Do not work around it.

## iCIMS (detected; read through `jsonld` only where allowed)
- `careers-X.icims.com/jobs/search` is disallowed by robots.txt for flydubai and Alaska Airlines.

## SAP SuccessFactors (detected; no reader yet)
- Seen on JetBlue (`career8.successfactors.com`), Ryanair (`career2.successfactors.eu`), Wizz Air
  (`*.jobs2web.com`). Next reader to build. Check robots.txt of the exact endpoint first.

## Oracle Taleo (detected; no reader yet)
- Seen on Qatar Airways (`aa115.taleo.net`) and easyJet (`easyjet.taleo.net`). Check robots.txt first.

## Careers sites that forbid automated reading (robots.txt)
American Airlines (aa.jobs), Delta, KLM, Qantas, IndiGo, LATAM, Ethiopian, AAR, Lufthansa Technik.

## Careers sites where the system wasn't visible
United, Southwest, Air Canada, Emirates Group, British Airways, Lufthansa Group, Cathay Pacific,
Air New Zealand, Bombardier, RTX, GE Aerospace, DFW Airport, Swissport, Menzies, ST Engineering: jobs load
by script. Look at where their Apply buttons lead.
