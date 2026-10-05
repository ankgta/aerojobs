"""Readers for each hiring system.

Every connector returns a list of "raw jobs": plain dicts with these keys
(only source_id, title and url are required):

    source_id, title, url, location, country_code, posted_date, posted_estimated,
    closing_date, work_mode, employment_type, department

Connectors never keep the employer's full job description.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
from html.parser import HTMLParser

from .common import parse_date, today
from .geo import lookup_country
from .http import PoliteClient


# ------------------------------------------------------------------ Workday
def _workday_parts(src: dict) -> tuple[str, str, str]:
    if src.get("host") and src.get("tenant") and src.get("site"):
        return src["host"], src["tenant"], src["site"]
    parts = urllib.parse.urlsplit(src["url"])
    host = parts.netloc
    tenant = host.split(".")[0]
    segments = [s for s in parts.path.split("/") if s]
    segments = [s for s in segments if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", s)]  # drop "en-US"
    if not segments:
        raise ValueError(f"Workday url needs the site name at the end: {src['url']}")
    return host, tenant, segments[0]


def posted_on_to_date(text: str | None, base: dt.date | None = None) -> tuple[str | None, bool]:
    """'Posted Today' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago' -> (date, is_estimate)."""
    if not text:
        return None, True
    base = base or today()
    t = text.lower()
    if "today" in t:
        return base.isoformat(), False
    if "yesterday" in t:
        return (base - dt.timedelta(days=1)).isoformat(), False
    m = re.search(r"(\d+)\+?\s*days?", t)
    if m:
        days = int(m.group(1))
        return (base - dt.timedelta(days=days)).isoformat(), "+" in t
    return None, True


def fetch_workday(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    host, tenant, site = _workday_parts(src)
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    jobs, offset, total = [], 0, None
    while True:
        data = client.post_json(api, {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""})
        postings = data.get("jobPostings") or []
        if total is None:
            total = data.get("total") or 0   # Workday only reports the total on the first page
        for p in postings:
            path = p.get("externalPath")
            if not path or not p.get("title"):
                continue
            posted, estimated = posted_on_to_date(p.get("postedOn"))
            loc = p.get("locationsText") or ""
            jobs.append({
                "source_id": path,
                "title": p["title"].strip(),
                "url": f"https://{host}/{site}{path}",
                "location": "" if re.match(r"^\d+ Locations?$", loc) else loc,
                "posted_date": posted,
                "posted_estimated": estimated,
                "detail_url": f"https://{host}/wday/cxs/{tenant}/{site}{path}",
            })
        offset += 20
        if not postings or offset >= total or len(jobs) >= max_jobs:
            break
    return jobs[:max_jobs]


def workday_detail(client: PoliteClient, job: dict) -> dict:
    """Read one Workday job's structured fields (country, exact dates, work mode)."""
    info = (client.get_json(job["detail_url"]) or {}).get("jobPostingInfo") or {}
    out = {}
    country = (info.get("country") or {}).get("descriptor")
    if country:
        out["country_code"] = lookup_country(country)
    if info.get("location"):
        out["location"] = info["location"]
    if info.get("startDate"):
        out["posted_date"] = parse_date(info["startDate"])
        out["posted_estimated"] = False
    if info.get("endDate"):
        out["closing_date"] = parse_date(info["endDate"])
    if info.get("timeType"):
        out["employment_type"] = info["timeType"]
    if info.get("remoteType"):
        out["work_mode"] = info["remoteType"]
    return out


# ------------------------------------------------------------------ Greenhouse
def fetch_greenhouse(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    data = client.get_json(f"https://boards-api.greenhouse.io/v1/boards/{src['board']}/jobs")
    jobs = []
    for j in data.get("jobs") or []:
        posted = parse_date(j.get("first_published"))
        jobs.append({
            "source_id": str(j["id"]),
            "title": j["title"].strip(),
            "url": j["absolute_url"],
            "location": (j.get("location") or {}).get("name") or "",
            "posted_date": posted,
            "posted_estimated": posted is None,
        })
    return jobs[:max_jobs]


# ------------------------------------------------------------------ Lever
def fetch_lever(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    host = "api.eu.lever.co" if src.get("region") == "eu" else "api.lever.co"
    jobs, skip = [], 0
    while True:
        page = client.get_json(f"https://{host}/v0/postings/{src['company']}?mode=json&skip={skip}&limit=100")
        if not isinstance(page, list) or not page:
            break
        for j in page:
            cats = j.get("categories") or {}
            posted = parse_date(j.get("createdAt"))
            jobs.append({
                "source_id": j["id"],
                "title": j["text"].strip(),
                "url": j["hostedUrl"],
                "location": cats.get("location") or "",
                "country_code": (j.get("country") or "").upper() or None,
                "posted_date": posted,
                "posted_estimated": posted is None,
                "work_mode": j.get("workplaceType"),
                "employment_type": cats.get("commitment"),
                "department": cats.get("team"),
            })
        if len(page) < 100 or len(jobs) >= max_jobs:
            break
        skip += 100
    return jobs[:max_jobs]


# ------------------------------------------------------------------ SmartRecruiters
def fetch_smartrecruiters(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    company = src["company"]
    jobs, offset = [], 0
    while True:
        data = client.get_json(f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset={offset}")
        content = data.get("content") or []
        for j in content:
            loc = j.get("location") or {}
            mode = "remote" if loc.get("remote") else ("hybrid" if loc.get("hybrid") else None)
            posted = parse_date(j.get("releasedDate"))
            place = loc.get("fullLocation") or ", ".join(x for x in (loc.get("city"), loc.get("country", "").upper()) if x)
            jobs.append({
                "source_id": str(j["id"]),
                "title": j["name"].strip(),
                "url": f"https://jobs.smartrecruiters.com/{company}/{j['id']}",
                "location": place,
                "country_code": (loc.get("country") or "").upper() or None,
                "posted_date": posted,
                "posted_estimated": posted is None,
                "work_mode": mode,
                "employment_type": (j.get("typeOfEmployment") or {}).get("label"),
                "department": (j.get("department") or {}).get("label"),
            })
        offset += len(content)
        if not content or offset >= (data.get("totalFound") or 0) or len(jobs) >= max_jobs:
            break
    return jobs[:max_jobs]


# ------------------------------------------------------------------ JobPosting data in web pages
class _LinkAndScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.ld_blocks: list[str] = []
        self._in_ld = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in_ld, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld_blocks.append("".join(self._buf))
            self._in_ld = False

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)


def _walk_ld(node):
    if isinstance(node, list):
        for n in node:
            yield from _walk_ld(n)
    elif isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            yield node
        for key in ("@graph", "itemListElement", "item"):
            if key in node:
                yield from _walk_ld(node[key])


def extract_job_postings(page_html: str) -> list[dict]:
    p = _LinkAndScriptParser()
    p.feed(page_html)
    found = []
    for block in p.ld_blocks:
        try:
            data = json.loads(html.unescape(block.strip()))
        except ValueError:
            continue
        found.extend(_walk_ld(data))
    return found


def jobposting_to_raw(jp: dict, page_url: str) -> dict | None:
    title = (jp.get("title") or "").strip()
    if not title:
        return None
    locs = jp.get("jobLocation") or []
    locs = locs if isinstance(locs, list) else [locs]
    place, country = "", None
    for loc in locs:
        addr = (loc or {}).get("address") or {}
        if isinstance(addr, str):
            place = place or addr
            continue
        c = addr.get("addressCountry")
        if isinstance(c, dict):
            c = c.get("name")
        country = country or lookup_country(c)
        place = place or ", ".join(x for x in (addr.get("addressLocality"), addr.get("addressRegion"), c) if x)
    remote = "remote" if str(jp.get("jobLocationType", "")).upper() == "TELECOMMUTE" else None
    emp = jp.get("employmentType")
    if isinstance(emp, list):
        emp = emp[0] if emp else None
    ident = jp.get("identifier")
    ident = ident.get("value") if isinstance(ident, dict) else ident
    posted = parse_date(jp.get("datePosted"))
    return {
        "source_id": str(ident or jp.get("url") or page_url),
        "title": html.unescape(title),
        "url": jp.get("url") or page_url,
        "location": place,
        "country_code": country,
        "posted_date": posted,
        "posted_estimated": posted is None,
        "closing_date": parse_date(jp.get("validThrough")),
        "work_mode": remote,
        "employment_type": emp,
    }


def list_job_links(client: PoliteClient, src: dict) -> list[str]:
    page = client.get_text(src["listing_url"])
    p = _LinkAndScriptParser()
    p.feed(page)
    pattern = re.compile(src.get("job_link_pattern") or r"/jobs?/")
    base = src["listing_url"]
    links = []
    for href in p.links:
        full = urllib.parse.urljoin(base, href.split("#")[0])
        if pattern.search(full) and full not in links and full.rstrip("/") != base.rstrip("/"):
            links.append(full)
    return links


def fetch_jsonld(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Two shapes: the listing page itself holds JobPosting data, or it links to job pages
    that do. Job pages are read later, only for links not seen before (see run.py)."""
    page = client.get_text(src["listing_url"])
    direct = [r for r in (jobposting_to_raw(jp, src["listing_url"]) for jp in extract_job_postings(page)) if r]
    if direct:
        return direct[:max_jobs]
    return [{"source_id": link, "title": "", "url": link, "detail_url": link, "needs_detail": True}
            for link in list_job_links(client, src)][:max_jobs]


def jsonld_detail(client: PoliteClient, job: dict) -> dict:
    postings = extract_job_postings(client.get_text(job["detail_url"]))
    raw = jobposting_to_raw(postings[0], job["url"]) if postings else None
    if not raw:
        return {}
    raw.pop("source_id", None)
    raw["url"] = job["url"]
    return raw


CONNECTORS = {
    "workday": (fetch_workday, workday_detail),
    "greenhouse": (fetch_greenhouse, None),
    "lever": (fetch_lever, None),
    "smartrecruiters": (fetch_smartrecruiters, None),
    "jsonld": (fetch_jsonld, jsonld_detail),
}
