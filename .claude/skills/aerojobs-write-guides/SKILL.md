---
name: aerojobs-write-guides
description: Write original aviation career guides for the AeroJobs site (aerojobs.work) that help Google AdSense approval and bring search traffic - pilot, cabin crew, engineering/MRO, airport and ATC career topics. Use when the owner asks for a guide, article, blog post or more site content, or when preparing the site for AdSense.
---

# Write AeroJobs career guides

Guides are the site's original content. AdSense rejects sites that only repeat job listings, and guides
also bring visitors from Google. Target: about 15 guides; 3 exist (`content/guides/`). Work in
**ankgta/aerojobs**.

## Pick the topic

Prefer topics people search for that match the site's jobs and role groups. Not yet written (from the
plan): how to become a commercial pilot in India; cabin crew requirements for Gulf airlines; what an MRO
technician earns; Part-66 B1 vs B2 licence explained; how cadet pilot programmes work and what they cost;
airline assessment day: what to expect; ground operations jobs with no experience; air traffic controller
selection by country; working in aviation in the UAE (visas, contracts); type ratings explained; aviation
jobs for career changers; how to read an airline job advert. Check `content/guides/` so you don't repeat.

## Research and accuracy

- Licences, regulations, salaries, age or height rules and visa rules change and differ by country and
  employer. Look them up (official regulator and employer pages) before stating them, link the source in
  the text, and say "as of <month year>" for figures. Never invent statistics, salaries or quotes.
- When unsure, say requirements vary and point readers to the employer and regulator.

## Write

- File: `content/guides/<short-slug>.md` (lowercase, dashes; the slug becomes the address).
- Front matter, exactly:
  ```
  ---
  title: <clear question or promise, under 65 characters>
  description: <one or two sentences, under 160 characters, used by Google>
  date: <YYYY-MM-DD>
  ---
  ```
- 900–1,400 words. Open with the answer in two or three sentences, then `##` sections a reader can scan,
  a short table where it helps comparison, and a closing section.
- Plain, friendly British-or-international English, short sentences, no hype, no emoji. Write for someone
  hoping to get hired.
- Link inside the site with the template function (never a hard-coded address):
  `[browse pilot jobs]({{ link('roles/pilots') }})`, `[open jobs]({{ link('') }}#jobs)`,
  `[guides]({{ link('guides') }})`, or another guide `{{ link('guides/<slug>') }}`. Role slugs: pilots,
  cabin-crew, engineering-maintenance, ground-operations, flight-operations, cargo-logistics,
  customer-service-sales, corporate.
- Add a "never pay to get a job" reminder where scams are plausible (cabin crew, cadets), linking
  `{{ link('guides/spot-fake-airline-job-offers') }}`.

## Check and publish

1. `python -m pytest -q tests` and `python -m site_builder.build --out /tmp/site`; open
   `/tmp/site/guides/<slug>/index.html` and confirm no `{{` remains and links resolve.
2. Commit (rebase first), push; the site rebuilds in about a minute.
3. Send the owner the guide's title and address and ask them to read it and add their own voice or
   experience. Their edits matter for AdSense ("original content").
4. Update the guide count in `docs/STATUS.md` and tick progress in `docs/ROADMAP.md`.
