# Aviation Jobs Portal — MVP Plan

Written 4 October 2026 with the owner.

> **Historical document (4 Oct 2026).** This is the original MVP plan. Two parts were changed later: the site is built with Python instead of Next.js, and there is no Supabase database (job data is a file in GitHub). See `DECISIONS.md` for why, and `STATUS.md` for where things stand now.

## Goal and scope

Launch a global aviation and airline job website in about 6 weeks that refreshes jobs automatically twice a day and is ready to apply for Google AdSense. Everything else (affiliates, paid listings, email alerts, the phone app) is built on top later.

**In the MVP**

- Jobs from about 50 large aviation employers worldwide (airlines, airports, maintenance (MRO) companies, manufacturers), English-language career pages first
- Automatic refresh every 12 hours, with expired jobs removed
- Search plus filters: country, job role, work mode (remote, hybrid, on-site), posted date (24 hours, 48 hours, last week, last month, older than a month)
- One page per job with a short summary and an Apply button that opens the employer's original page
- About 15 original guide articles, plus the pages AdSense expects (About, Contact, Privacy Policy, Terms)
- Google AdSense applied for, plus Google Search Console and Google for Jobs setup

**Not in the MVP (later)**

- Affiliate links, paid featured jobs, job alert emails, user accounts, employers posting jobs themselves, the phone app
- Non-English career pages
- Job-board partner feeds (Adzuna, Jooble). These are easy to add in week 7 or 8.

**Done means:** the site is live on your own domain, shows at least 500 current jobs, refreshes itself without you touching it, and the AdSense application is submitted.

## Tech stack and cost

The MVP runs on free plans that allow ads, so the only fixed cost is the domain (about $10–15 a year) plus a few dollars a month if AI sorting is used.

| Piece | Tool | Why this one | Cost |
| --- | --- | --- | --- |
| Website | Next.js, hosted on Cloudflare | Free plan allows commercial sites with ads | $0 |
| Database | Supabase (Postgres) | Free plan: 500 MB, enough for 100,000+ jobs | $0 |
| Job fetcher | Python script run on a timer by GitHub Actions | Runs every 12 hours with no server to manage | $0 |
| Domain | Cloudflare Registrar or any registrar | One place for domain and hosting | \~$10–15/year |
| Sorting jobs into roles | Keyword rules first, Claude Haiku for unclear jobs | Most jobs sort by title alone | $0–5/month |
| Traffic and ads | Google Search Console, Google Analytics, AdSense | Standard and free | $0 |

**Two hosting traps to avoid**

- **Vercel's free (Hobby) plan does not allow ads.** It is limited to non-commercial personal use, so a site with AdSense needs its $20/month Pro plan ([Vercel](https://vercel.com/docs/limits/fair-use-guidelines)). Cloudflare's free tier has no such restriction ([source](https://thesearchsherpa.com/?p=2188)).
- **Supabase pauses free projects after 7 days with no activity** ([source](https://www.itpathsolutions.com/supabase-free-tier-limits)). The fetcher writes to the database every 12 hours, which keeps it awake.

**When to start paying:** once traffic passes roughly 50,000 visits a month, move the database to Supabase Pro ($25/month) for backups and no pausing. Ad income should cover it by then.

## Features

### How jobs are collected

The fetcher reads each employer's career page in the cheapest reliable way available, in this order:

1. **Hiring-system connectors.** Most airlines use Workday, SAP SuccessFactors, Oracle Taleo, Greenhouse, Lever or SmartRecruiters. One connector per system covers every employer on it.
2. **Built-in job data.** Many career pages include Google's JobPosting data inside the page. One general reader handles all of them.
3. **Reading the page itself.** A custom reader per site, only for important employers the first two methods miss.

Skipped: LinkedIn, Indeed and any site whose rules forbid automated collection.

### What the fetcher does every 12 hours

1. Loads the employer list (name, career page link, hiring system, country).
2. Collects all open jobs from each employer, pausing between requests.
3. Cleans each job: title, location, country, work mode (remote, hybrid, on-site), posted date, closing date.
4. Sorts each job into a role category by its title, using AI only for unclear titles.
5. Saves new jobs and updates changed ones.
6. Marks jobs missing from two runs in a row as expired, and hides them.
7. Emails you a short report if an employer returned zero jobs, which usually means its page changed.

**Dates:** when a page shows no posting date, the site uses the date the job was first found, so the date filters still work. Closing dates are shown only when the employer gives one.

### Role categories

Pilots · Cabin crew · Aircraft engineering and maintenance (MRO) · Ground operations and airport services · Air traffic and flight operations · Cargo and logistics · Customer service and sales · Corporate (IT, finance, HR, other)

### Filters and sorting

| Filter | Options |
| --- | --- |
| Keyword search | Job title, company |
| Country | All countries with open jobs, grouped by region |
| Job role | The 8 role categories above |
| Work mode | Remote, Hybrid, On-site |
| Posted | Last 24 hours, last 48 hours, last week, last month, older than a month |
| Company type | Airline, airport, MRO, manufacturer, other |
| Sort by | Newest first (default), closing soonest |

### Pages

- **Home and search:** search box, filters, job list, newest first.
- **Job page:** title, company, location, work mode, dates, a short summary written by the site (not the employer's full text), and an Apply button that opens the original page. Each job page carries Google's JobPosting data so it can appear in Google for Jobs.
- **Company pages:** for example "Emirates jobs", listing all of one employer's open roles.
- **Country and role pages:** for example "Cabin crew jobs in the UAE". These pull in Google search traffic.
- **Guides, About, Contact, Privacy Policy, Terms:** needed for AdSense (next section).

## AdSense readiness checklist

AdSense approves sites with original, high-quality content that attracts an audience, run by someone 18 or older ([Google](https://support.google.com/adsense/answer/9724)). A site that only repeats other sites' job listings is the most common reason job boards get rejected, so the MVP adds its own content before applying.

**Original content**

- [ ] 15 guide articles of 800+ words each, written with Claude and edited in your own voice (for example: how to become a pilot in India, cabin crew requirements for Gulf airlines, what an MRO technician earns)
- [ ] Short, rewritten job summaries instead of the employer's full description
- [ ] Company pages with a 2–3 sentence intro about each employer

**Required pages**

- [ ] About (who runs the site and why)
- [ ] Contact (a working email address or form)
- [ ] Privacy Policy that mentions Google ads and cookies
- [ ] Terms of Use
- [ ] A consent banner from a Google-certified provider for visitors in Europe and the UK (Google offers a free one inside AdSense)

**Site quality**

- [ ] Live on your own domain with a menu that links to every section
- [ ] Works well on phones and loads quickly
- [ ] No broken links or empty pages
- [ ] At least 500 live jobs
- [ ] Submitted to Google Search Console, with pages starting to appear in Google

**When to apply:** about 2–4 weeks after launch, once the guides are up and Google has started showing your pages. Review usually takes a few days to a few weeks. If rejected, Google states the reason; fix it and reapply.

## Week-by-week build plan

The build takes about 6 weeks at a few hours a week, with the AdSense application in week 8. Claude writes the code and content; your part is mostly creating accounts, pasting keys, checking results and making decisions. Claude Code is the easiest tool for weeks 2–5 because it can run, test and deploy the code itself.

| Week | Goal | Claude does | You do |
| --- | --- | --- | --- |
| 1 | Foundations | Researches 50 global employers: career page links, hiring system, country. Suggests site names and checks domain availability. | Pick the name, buy the domain, create the accounts in the next section, approve the employer list. |
| 2 | Job fetcher | Builds connectors for the main hiring systems, the cleaning and role sorting, and the 12-hour schedule. | Paste the database and GitHub keys when asked. Spot-check 20 jobs against the original pages. |
| 3 | Website | Builds the search page, filters, sorting, job pages, company, country and role pages. Adds Google's JobPosting data. | Click through on your phone and laptop. List anything confusing or ugly. |
| 4 | Content and legal pages | Drafts 15 guides, About, Contact, Privacy Policy and Terms. Writes company intros. | Read and edit each guide so it sounds like you. Add your own aviation knowledge where you can. |
| 5 | Launch | Connects the domain, sets up Search Console, Analytics and the zero-jobs alert. Fixes issues. | Do a final check. Share the site in aviation groups on LinkedIn, Facebook and Reddit. |
| 6 | Polish and grow | Adds 20–30 more employers. Fixes broken connectors. Improves pages based on what visitors use. | Watch Search Console. Collect feedback from a few real job seekers. |
| 7–8 | AdSense | Checks the site against the readiness checklist and fixes gaps. | Apply for AdSense. Once approved, Claude places the ad code. |

After each week, ask Claude for a short check: what works, what broke, what is next.

## Accounts and things only you can do

Create these six accounts in week 1, all with one email address dedicated to the site. Claude cannot create accounts, enter passwords or make payments for you.

- [ ] A new Gmail address for the site (for example hello.yoursite@gmail.com)
- [ ] GitHub: stores the code and runs the job fetcher on its timer
- [ ] Supabase: the database
- [ ] Cloudflare: domain and website hosting
- [ ] Anthropic API key with a $5–10 spending limit (only if AI role sorting is used)
- [ ] Google Search Console, Google Analytics, and later AdSense, all with the site's Gmail

**Also yours to do**

- Choose the site name and buy the domain
- Approve the employer list and the role categories
- Edit the guide articles so they reflect your voice and knowledge
- Check that the Privacy Policy and Terms fit your country. Claude can draft them, but it is not a lawyer, so a quick professional review is worth it once the site earns money.
- Keep passwords and keys private. Paste keys only where Claude Code asks for them, never into chat messages or public pages.

## Launch checklist and success targets

**Before launch**

- [ ] 500+ live jobs from 50 employers, spot-checked against the original pages
- [ ] Every filter and date option returns sensible results
- [ ] Apply buttons open the right employer page
- [ ] The fetcher has run on its own for 7 days without failing
- [ ] Expired jobs disappear within 24 hours
- [ ] Site tested on a phone and a laptop
- [ ] Search Console connected and sitemap submitted
- [ ] Google's Rich Results Test shows job pages as valid JobPosting

**Targets for the first 3 months**

| Measure | Month 1 | Month 3 |
| --- | --- | --- |
| Employers covered | 50 | 150 |
| Live jobs | 500 | 2,000 |
| Monthly visitors | 500 | 5,000 |
| Clicks on Apply buttons | 100 | 1,000 |
| Pages showing in Google | 200 | 2,000 |
| AdSense | Applied | Approved and earning |

These targets are estimates, not guarantees. Clicks on Apply buttons matter most: they show the site is useful, and they are what employers will pay for later.

## After the MVP

Add these in order of effort, each on top of the working site:

1. **Job-board partner feeds (Adzuna, Jooble):** more jobs plus pay-per-click income. About 1 week.
2. **Job alert emails:** visitors subscribe to a role and country. This brings them back and builds a list to sell sponsor slots in. About 1–2 weeks.
3. **Affiliate links:** pilot training, cabin crew courses, exam prep, CV services and pilot gear, placed inside the guides. Apply once traffic is steady.
4. **Paid featured jobs:** employers and schools pay through a Stripe payment link to pin a listing at the top. About 1 week.
5. **More employers and languages:** non-English career pages (German, French, Spanish, Arabic).
6. **Installable phone version (PWA):** the site installs like an app, at almost no cost.
7. **Full phone app:** only once there are regular users asking for it.

## Sources

- [Vercel Fair Use Guidelines](https://vercel.com/docs/limits/fair-use-guidelines)
- [Is Vercel free? (The Search Sherpa)](https://thesearchsherpa.com/?p=2188)
- [Supabase free tier limits 2026 (IT Path Solutions)](https://www.itpathsolutions.com/supabase-free-tier-limits)
- [Eligibility requirements for AdSense (Google)](https://support.google.com/adsense/answer/9724)
