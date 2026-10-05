"""Build the website from the job data. Run with:  python -m site_builder.build

Writes a complete static website into public/ that any static host (Cloudflare Pages)
can serve. Use --preview to build with sample data and links that work from files.
"""
from __future__ import annotations

import argparse
from html import escape as html_escape
import datetime as dt
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from fetcher.common import (COMPANY_TYPES, CONFIG_DIR, DATA_DIR, ROOT, load_employers,
                            load_site_config, read_json, slugify, today)
from fetcher.geo import REGION_ORDER, country_name
from fetcher.roles import ROLE_SHORT, ROLES
from fetcher.run import is_visible

HERE = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
EEA_UK = ("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE "
          "IS LI NO GB CH").split()
EMPLOYMENT_SCHEMA = {"Full-time": "FULL_TIME", "Part-time": "PART_TIME", "Contract": "CONTRACTOR",
                     "Internship": "INTERN"}
MAX_ROWS_ON_LIST_PAGES = 100

# Read by Cloudflare Pages. Scripts may only load over secure https connections (AdSense
# loads from many Google addresses, so they cannot be listed one by one without breaking ads).
SECURITY_HEADERS = """/*
  Content-Security-Policy: default-src 'self' https: data:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' https: data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
/data/*
  Cache-Control: public, max-age=600
"""


# ------------------------------------------------------------------ helpers
def human_date(iso: str | None) -> str:
    if not iso:
        return ""
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def ago(iso: str, ref: dt.date) -> str:
    days = (ref - dt.date.fromisoformat(iso)).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 60:
        return "1 month ago"
    return f"{days // 30} months ago"


def initials(name: str) -> str:
    words = [w for w in re.split(r"[\s&-]+", name) if w and w[0].isalnum()]
    return "".join(w[0] for w in words[:2]).upper() or "?"


def tone(slug: str) -> int:
    """Same rule as search.js: sum of character codes, 8 colour tones."""
    return sum(ord(c) for c in slug) % 8


def article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def job_summary(job: dict) -> str:
    """A short description written by the site from the job's facts (never the employer's text)."""
    role = ROLES.get(job.get("role"), "aviation").split(" (")[0].lower()
    s = [f"{job['company']} has {article(role)} {role} vacancy open: {job['title']}."]
    if job.get("location"):
        s.append(f"The role is based in {job['location']}"
                 + (f", {job['country']}." if job.get("country") and job["country"] not in job["location"] else "."))
    else:
        s.append("The employer's page gives the location details.")
    kind = ", ".join(x for x in (job.get("work_mode", "").lower(), (job.get("employment_type") or "").lower()) if x)
    if kind:
        s.append(f"It is listed as {article(kind)} {kind} position.")
    if job.get("posted_estimated"):
        s.append(f"We first found it on {human_date(job['posted_date'])}.")
    else:
        s.append(f"It was posted on {human_date(job['posted_date'])}.")
    if job.get("closing_date"):
        s.append(f"Applications close on {human_date(job['closing_date'])}.")
    s.append(f"You apply on {job['company']}'s own careers site, where the full job description is published.")
    return " ".join(s)


def job_posting_jsonld(job: dict, site: dict, page_url: str) -> str | None:
    if not job.get("country_code"):
        return None   # Google needs at least a country; skip rather than guess
    locality = (job.get("location") or "").split(",")[0].strip()
    data = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": job["title"],
        "description": f"<p>{html_escape(job['summary'])}</p>",
        "datePosted": job["posted_date"],
        "hiringOrganization": {"@type": "Organization", "name": job["company"]},
        "identifier": {"@type": "PropertyValue", "name": job["company"], "value": job["id"]},
        "directApply": False,
        "url": page_url,
    }
    if job.get("closing_date"):
        data["validThrough"] = job["closing_date"] + "T23:59:59"
    if job.get("employment_type") in EMPLOYMENT_SCHEMA:
        data["employmentType"] = EMPLOYMENT_SCHEMA[job["employment_type"]]
    address = {"@type": "PostalAddress", "addressCountry": job["country_code"]}
    if locality and locality.lower() != (job.get("country") or "").lower():
        address["addressLocality"] = locality
    if job.get("work_mode") == "Remote":
        data["jobLocationType"] = "TELECOMMUTE"
        data["applicantLocationRequirements"] = {"@type": "Country", "name": job["country"]}
    else:
        data["jobLocation"] = {"@type": "Place", "address": address}
    # Escape < > & so nothing inside the data can close the script block or add markup.
    return (json.dumps(data, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def read_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        _, fm, text = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    return meta, text.strip()


# ------------------------------------------------------------------ builder
class Builder:
    def __init__(self, out: Path, preview: bool, jobs_file: Path, employers_file: Path | None):
        self.out = out
        self.preview = preview
        self.site = load_site_config()
        self.site["site_url"] = self.site["site_url"].rstrip("/")
        self.ref_date = today()
        self.employers = {e["slug"]: e for e in load_employers(employers_file)}
        store = read_json(jobs_file, {"jobs": {}})
        self.updated_at = store.get("updated_at")
        self.jobs = sorted((j for j in store["jobs"].values() if is_visible(j)),
                           key=lambda j: (j["posted_date"], j["id"]), reverse=True)
        for j in self.jobs:
            j["summary"] = job_summary(j)
            j["path"] = f"jobs/{j['slug']}"
            j["role_label"] = ROLES.get(j["role"], ROLES["corporate"])
            j["posted_ago"] = ago(j["posted_date"], self.ref_date)
            j["company_slug"] = j["employer"]
            days = (self.ref_date - dt.date.fromisoformat(j["posted_date"])).days
            j["is_new"] = days <= 2
            closes = (dt.date.fromisoformat(j["closing_date"]) - self.ref_date).days if j.get("closing_date") else None
            j["closing_soon"] = closes is not None and 0 <= closes <= 7
            j["initials"] = initials(j["company"])
            j["tone"] = tone(j["employer"])
        self.env = Environment(loader=FileSystemLoader(HERE / "templates"),
                               autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
        self.env.globals.update(site=self.site, roles=ROLES, role_short=ROLE_SHORT, company_types=COMPANY_TYPES,
                                preview=self.preview, human_date=human_date, year=self.ref_date.year)
        self.pages: list[str] = []   # paths for the sitemap

    # links: absolute "/x/" on the live site; relative "../x/index.html" in preview files
    def _root(self, out_path: str) -> str:
        if not self.preview:
            return "/"
        return "../" * out_path.count("/")

    @staticmethod
    def _out_path(path: str) -> str:
        return path if path.endswith(".html") else (f"{path}/index.html" if path else "index.html")

    def linker(self, path: str):
        root = self._root(self._out_path(path))
        suffix = "index.html" if self.preview else ""

        def link(p: str) -> str:
            if p.endswith((".html", ".xml", ".json", ".css", ".js", ".txt", ".webmanifest")):
                return root + p
            return root + (p + "/" if p else "") + suffix
        return link

    def render(self, template: str, path: str, sitemap: bool = True, **ctx) -> None:
        """path: '' for home, 'jobs/x' for a folder page, '404.html' for a file."""
        out_path = self._out_path(path)
        root = self._root(out_path)
        suffix = "index.html" if self.preview else ""
        link = self.linker(path)
        canonical = f"{self.site['site_url']}/{path + '/' if path and not path.endswith('.html') else ''}"
        html = self.env.get_template(template).render(link=link, asset=lambda p: root + p, root=root,
                                                      link_suffix=suffix, canonical=canonical, **ctx)
        target = self.out / out_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        if sitemap and not path.endswith(".html"):
            self.pages.append(path)

    def build(self) -> None:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copytree(HERE / "static", self.out / "static")

        jobs = self.jobs
        by_company = defaultdict(list)
        by_country = defaultdict(list)
        by_role = defaultdict(list)
        for j in jobs:
            by_company[j["employer"]].append(j)
            if j.get("country_code"):
                by_country[j["country_code"]].append(j)
            by_role[j["role"]].append(j)

        countries = [{"code": c, "name": country_name(c), "slug": slugify(country_name(c)),
                      "region": lst[0]["region"], "count": len(lst)} for c, lst in by_country.items()]
        countries.sort(key=lambda c: c["name"])
        regions = [(r, [c for c in countries if c["region"] == r]) for r in REGION_ORDER + ["Other"]]
        regions = [(r, cs) for r, cs in regions if cs]
        companies = [{**self.employers.get(s, {"name": lst[0]["company"], "type": lst[0]["company_type"]}),
                      "slug": s, "count": len(lst)} for s, lst in by_company.items()]
        companies.sort(key=lambda c: c["name"].lower())
        guides = self.load_guides()
        stats = {"jobs": len(jobs), "companies": len(companies), "countries": len(countries)}
        common = dict(stats=stats, updated=human_date(self.updated_at[:10]) if self.updated_at else None)

        # home + search
        self.render("home.html", "", jobs=jobs[:25], regions=regions, guides=guides[:6],
                    role_counts=Counter(j["role"] for j in jobs),
                    type_counts=Counter(j["company_type"] for j in jobs), **common)
        # job pages
        for j in jobs:
            similar = [x for x in by_role[j["role"]] if x["id"] != j["id"]][:5]
            page_url = f"{self.site['site_url']}/{j['path']}/"
            self.render("job.html", j["path"], job=j, similar=similar,
                        jsonld=Markup(job_posting_jsonld(j, self.site, page_url) or ""),
                        employer=self.employers.get(j["employer"], {}), **common)
        # companies
        self.render("companies.html", "companies", companies=companies, section="companies", **common)
        for c in companies:
            lst = by_company[c["slug"]]
            self.render("listing.html", f"companies/{c['slug']}", heading=f"{c['name']} jobs",
                        intro=self.company_intro(c, lst), jobs=lst[:MAX_ROWS_ON_LIST_PAGES],
                        total=len(lst), search_query=f"company={c['slug']}", **common)
        # countries
        self.render("countries.html", "countries", regions=regions, section="countries", **common)
        for c in countries:
            lst = by_country[c["code"]]
            top = Counter(j["role"] for j in lst).most_common(1)[0][0]
            intro = (f"{len(lst)} open aviation {'job' if len(lst) == 1 else 'jobs'} in {c['name']} from "
                     f"{len({j['employer'] for j in lst})} employers. The most common area right now is "
                     f"{ROLES[top].split(' (')[0].lower()}.")
            self.render("listing.html", f"countries/{c['slug']}", heading=f"Aviation jobs in {c['name']}",
                        intro=intro, jobs=lst[:MAX_ROWS_ON_LIST_PAGES], total=len(lst),
                        search_query=f"country={c['code']}", **common)
        # roles (always all eight, so the menu never leads nowhere)
        for key, label in ROLES.items():
            lst = by_role.get(key, [])
            intro = self.role_intro(key, lst)
            self.render("listing.html", f"roles/{key}", heading=f"{label.split(' (')[0]} jobs",
                        intro=intro, jobs=lst[:MAX_ROWS_ON_LIST_PAGES], total=len(lst),
                        search_query=f"role={key}", **common)
        # guides and fixed pages
        self.render("guides.html", "guides", guides=guides, section="guides", **common)
        for g in guides:
            self.render("article.html", f"guides/{g['slug']}", page=g, kind="guide", section="guides", **common)
        for path in sorted((CONTENT / "pages").glob("*.md")):
            meta, body = read_markdown(path)
            vars_ = dict(site=self.site, updated=human_date(self.ref_date.isoformat()), link=self.linker(path.stem))
            body = self.env.from_string(body).render(**vars_)
            meta = {k: self.env.from_string(v).render(**vars_) for k, v in meta.items()}
            page = {**meta, "html": Markup(markdown.markdown(body, extensions=["tables"]))}
            self.render("article.html", path.stem, page=page, kind="page", **common)
        self.render("404.html", "404.html", sitemap=False, **common)

        self.write_search_index(jobs)
        self.write_seo_files()
        print(f"Built {len(self.pages)} pages into {self.out} "
              f"({stats['jobs']} jobs, {stats['companies']} companies, {stats['countries']} countries)")

    def company_intro(self, c: dict, lst: list[dict]) -> str:
        if c.get("intro"):
            return c["intro"]
        kind = COMPANY_TYPES.get(c.get("type"), "aviation employer").lower()
        hq = country_name(c.get("country"))
        n_countries = len({j["country_code"] for j in lst if j.get("country_code")})
        return (f"{c['name']} is {article(kind)} {kind}" + (f" headquartered in {hq}" if hq else "") + ". "
                f"It currently lists {len(lst)} open {'role' if len(lst) == 1 else 'roles'}"
                + (f" across {n_countries} {'country' if n_countries == 1 else 'countries'}" if n_countries else "")
                + ". Every job links to its own careers site to apply.")

    def role_intro(self, key: str, lst: list[dict]) -> str:
        if not lst:
            return "No open roles in this group right now. New jobs are added twice a day."
        n_c = len({j["country_code"] for j in lst if j.get("country_code")})
        return (f"{len(lst)} open {'role' if len(lst) == 1 else 'roles'} from "
                f"{len({j['employer'] for j in lst})} employers in {n_c} "
                f"{'country' if n_c == 1 else 'countries'}, newest first.")

    def load_guides(self) -> list[dict]:
        guides = []
        for path in sorted((CONTENT / "guides").glob("*.md")):
            meta, body = read_markdown(path)
            body = self.env.from_string(body).render(site=self.site, link=self.linker(f"guides/{path.stem}"))
            words = len(re.findall(r"\w+", body))
            guides.append({**meta, "slug": path.stem, "words": words, "minutes": max(1, round(words / 220)),
                           "html": Markup(markdown.markdown(body, extensions=["tables"]))})
        guides.sort(key=lambda g: g.get("date", ""), reverse=True)
        return guides

    def write_search_index(self, jobs: list[dict]) -> None:
        rows = [{
            "i": j["id"], "t": j["title"], "c": j["company"], "cs": j["employer"], "ct": j["company_type"],
            "r": j["role"], "cc": j.get("country_code") or "", "cn": j.get("country") or "",
            "rg": j.get("region") or "", "l": j.get("location") or "", "w": j["work_mode"],
            "p": j["posted_date"], "x": j.get("closing_date") or "", "u": j["path"],
            "a": j["initials"], "o": j["tone"],
        } for j in jobs]
        path = self.out / "data" / "jobs-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"built": self.ref_date.isoformat(), "jobs": rows},
                                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def write_seo_files(self) -> None:
        manifest = {
            "name": self.site["site_name"], "short_name": self.site["site_name"][:12],
            "start_url": "./" if self.preview else "/", "display": "standalone",
            "background_color": "#F4F8FC", "theme_color": "#FFFFFF",
            "icons": [{"src": "static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "static/icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
        }
        (self.out / "site.webmanifest").write_text(json.dumps(manifest, indent=1))
        base = self.site["site_url"]
        urls = "\n".join(f"  <url><loc>{base}/{p + '/' if p else ''}</loc></url>" for p in self.pages)
        (self.out / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n', encoding="utf-8")
        (self.out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")
        if not self.preview:
            (self.out / "_headers").write_text(SECURITY_HEADERS)
        client = self.site.get("adsense_client", "")
        if client.startswith("ca-pub-"):
            pub = client.replace("ca-", "")
            (self.out / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="use sample data and file-friendly links")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.preview:
        b = Builder(Path(args.out or ROOT / "preview"), True, DATA_DIR / "sample" / "jobs.json",
                    DATA_DIR / "sample" / "employers.yaml")
    else:
        b = Builder(Path(args.out or ROOT / "public"), False, DATA_DIR / "jobs.json", CONFIG_DIR / "employers.yaml")
    b.build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
