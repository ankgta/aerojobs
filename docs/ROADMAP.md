# Roadmap

## MVP: what's left before applying for AdSense

- [x] Site live on its own domain, refreshing itself twice a day
- [x] About, Contact, Privacy Policy, Terms
- [x] Phone-friendly, fast, no broken links (tested)
- [x] 500+ live jobs (3,598)
- [ ] ~12 more original guides, 800+ words each, edited by the owner
- [ ] Short intros on the main employer pages
- [ ] More airline coverage (pilots and cabin crew): SuccessFactors and Taleo readers, .aero directory
- [ ] Google Search Console connected, sitemap submitted, pages appearing in Google
- [ ] Google Analytics ID in `config/site.yaml`
- [ ] Check job pages in Google's Rich Results Test
- [ ] Fetcher runs on its own for 7 days without failing
- [ ] Apply for AdSense; set up its European consent message; turn on Auto ads after approval

## Scale

- [ ] Before ~15,000 jobs: generate job pages on demand (Cloudflare Functions, still free) instead of one
      file per job, because of the 20,000-file limit
- [ ] Keep GitHub Actions minutes under the free 2,000 a month (or make the repository public)

## After the MVP, in order

1. Job-board partner feeds (Adzuna, Jooble): more jobs plus pay-per-click income. About 1 week.
2. Job alert emails (needs a small database again, e.g. Supabase) with sponsor slots. About 1–2 weeks.
3. Affiliate links inside guides: pilot training, cabin crew courses, exam prep, CV services, pilot gear
   (networks: Impact, CJ, Awin, Amazon Associates; or direct deals with schools).
4. Paid featured jobs via a Stripe payment link. About 1 week.
5. Non-English careers pages (German, French, Spanish, Arabic).
6. Full phone app, only when regular users ask for it (the site already installs to the home screen).
