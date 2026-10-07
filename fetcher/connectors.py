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
    """Links to job pages on a listing page. If listing_url contains {page}, pages
    start..start+max_pages-1 are read until one adds no new links."""
    pattern = re.compile(src.get("job_link_pattern") or r"/jobs?/")
    tpl = src["listing_url"]
    pages = range(int(src.get("first_page", 0)), int(src.get("first_page", 0)) + int(src.get("max_pages", 30))) if "{page}" in tpl else [None]
    links: list[str] = []
    for n in pages:
        base = tpl.format(page=n) if n is not None else tpl
        p = _LinkAndScriptParser()
        p.feed(client.get_text(base))
        before = len(links)
        for href in p.links:
            full = urllib.parse.urljoin(base, href.split("#")[0])
            if src.get("strip_query"):
                full = full.split("?")[0]
            if pattern.search(full) and full not in links and full.rstrip("/") != base.rstrip("/"):
                links.append(full)
        if len(links) == before:
            break
    return links


def fetch_jsonld(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Two shapes: the listing page itself holds JobPosting data, or it links to job pages
    that do. Job pages are read later, only for links not seen before (see run.py)."""
    first_url = src["listing_url"].format(page=src.get("first_page", 0)) if "{page}" in src["listing_url"] else src["listing_url"]
    page = client.get_text(first_url)
    direct = [r for r in (jobposting_to_raw(jp, first_url) for jp in extract_job_postings(page)) if r]
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


# ------------------------------------------------------------------ SuccessFactors Career Site Builder
class _SFListingParser(HTMLParser):
    """Extract jobs from SAP SuccessFactors Career Site Builder listing pages.

    The pages render jobs in HTML table rows.  Each row contains an <a> tag
    linking to /job/<slug>/<id>/ (or /<unit>/job/<slug>/<id>/) with the job
    title as the link text.  The location is the next non-empty text content
    in the same <tr>, after the title.
    """
    def __init__(self):
        super().__init__()
        self.jobs: list[dict] = []
        self.total: int | None = None
        # row tracking
        self._in_tr = False
        self._tds: list[str] = []
        self._td_buf: list[str] = []
        self._in_td = False
        # link tracking
        self._job_href: str | None = None
        self._job_title: str | None = None
        self._in_link = False
        self._link_buf: list[str] = []
        # total-count tracking
        self._all_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self._in_tr = True
            self._tds = []
            self._job_href = None
            self._job_title = None
        elif tag in ("td", "th") and self._in_tr:
            self._in_td = True
            self._td_buf = []
        elif tag == "a":
            href = a.get("href", "")
            if self._in_tr and re.search(r"/job/.+/\d+/?$", href):
                self._job_href = href
                self._in_link = True
                self._link_buf = []

    def handle_data(self, data):
        if self._in_link:
            self._link_buf.append(data)
        if self._in_td:
            self._td_buf.append(data)
        self._all_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._in_link:
            self._job_title = "".join(self._link_buf).strip()
            self._in_link = False
        elif tag in ("td", "th") and self._in_td:
            self._tds.append("".join(self._td_buf).strip())
            self._in_td = False
        elif tag == "tr" and self._in_tr:
            self._in_tr = False
            if self._job_href and self._job_title:
                # location = first non-empty td text that isn't the title
                location = ""
                for cell in self._tds:
                    if cell and cell != self._job_title:
                        location = cell
                        break
                self.jobs.append({
                    "href": self._job_href,
                    "title": self._job_title,
                    "location": location,
                })

    def close(self):
        super().close()
        # try to find total count from text like "Results 1 – 25 of 70"
        text = " ".join(self._all_text)
        m = re.search(r"of\s+(\d+)\s+(?:results?|jobs?|positions?|openings?)", text, re.I)
        if m:
            self.total = int(m.group(1))


def _clean_sf_location(raw: str, title: str) -> str:
    """Extract a clean location from the messy SuccessFactors cell text.

    SF listing cells often contain the title repeated, department names,
    dates, and job IDs alongside the actual location.  This picks out the
    location line by looking for the first comma-containing line that isn't
    the title itself.
    """
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    # drop lines that ARE the title (often repeated)
    lines = [ln for ln in lines if ln != title]
    # drop pure-digit lines (job IDs like "58082")
    lines = [ln for ln in lines if not re.fullmatch(r"\d+", ln)]
    # drop date-like lines ("5 Oct 2026", "12 September 2025")
    lines = [ln for ln in lines if not re.fullmatch(r"\d{1,2}\s+\w+\s+\d{4}", ln)]
    # first remaining line with a comma is most likely the location
    for ln in lines:
        if "," in ln:
            return ln
    # fallback: first remaining non-empty line (might be a department or city)
    return lines[0] if lines else ""


def fetch_successfactors(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """SAP SuccessFactors Career Site Builder (careers.example.com/search/…)."""
    base = src["url"].rstrip("/")
    jobs: list[dict] = []
    offset, total = 0, None
    while True:
        url = f"{base}/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow={offset}"
        page_html = client.get_text(url)
        parser = _SFListingParser()
        parser.feed(page_html)
        parser.close()
        if total is None and parser.total is not None:
            total = parser.total
        if not parser.jobs:
            break
        for j in parser.jobs:
            full_url = urllib.parse.urljoin(base + "/", j["href"])
            m = re.search(r"/(\d+)/?$", j["href"])
            source_id = m.group(1) if m else j["href"]
            location = _clean_sf_location(j["location"], j["title"])
            jobs.append({
                "source_id": source_id,
                "title": j["title"].strip(),
                "url": full_url,
                "location": location,
                "posted_estimated": True,
            })
        offset += 25
        if (total and offset >= total) or len(jobs) >= max_jobs:
            break
    return jobs[:max_jobs]


# ------------------------------------------------------------------ Oracle Recruiting Cloud
def fetch_oracle(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Oracle Cloud HCM careers sites (…oraclecloud.com/hcmUI/CandidateExperience/…/sites/<site>)."""
    host, site = src["host"], src["site"]
    lang = src.get("lang", "en")
    jobs, offset = [], 0
    while True:
        url = (f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
               f"&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber={site},"
               f"limit=25,offset={offset},sortBy=POSTING_DATES_DESC")
        data = client.get_json(url)
        items = (data.get("items") or [{}])[0]
        reqs = items.get("requisitionList") or []
        total = items.get("TotalJobsCount") or 0
        for r in reqs:
            if not r.get("Title") or not r.get("Id"):
                continue
            posted = parse_date(r.get("PostedDate"))
            mode = (r.get("WorkplaceType") or r.get("WorkplaceTypeCode") or "")
            jobs.append({
                "source_id": str(r["Id"]),
                "title": r["Title"].strip(),
                "url": f"https://{host}/hcmUI/CandidateExperience/{lang}/sites/{site}/job/{r['Id']}",
                "location": r.get("PrimaryLocation") or "",
                "country_code": (r.get("PrimaryLocationCountry") or "").upper() or None,
                "posted_date": posted,
                "posted_estimated": posted is None,
                "closing_date": parse_date(r.get("ExternalPostedEndDate") or r.get("PostingEndDate")),
                "work_mode": mode.lower().replace("_", "-") if mode else None,
                "employment_type": r.get("JobSchedule") or r.get("ContractType"),
                "department": r.get("Organization") or r.get("JobFamily"),
            })
        offset += 25
        if not reqs or offset >= total or len(jobs) >= max_jobs:
            break
    return jobs[:max_jobs]


# ------------------------------------------------------------------ Oracle Taleo Enterprise
class _TaleoPortalParser(HTMLParser):
    """Extract the portal ID from a Taleo jobsearch.ftl page."""
    def __init__(self):
        super().__init__()
        self.portal_id: str | None = None
        self._in_script = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._in_script = True
            self._buf = []

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            text = "".join(self._buf)
            # Look for portal ID in various forms: portal:123, "portal":"123", portalId=123
            m = re.search(r'["\']?portal(?:Id)?["\']?\s*[:=]\s*["\']?(\d+)["\']?', text, re.I)
            if m and not self.portal_id:
                self.portal_id = m.group(1)
            self._in_script = False


def _taleo_get_portal(client: PoliteClient, host: str, section: str = "2") -> str | None:
    """Fetch the Taleo jobsearch page and extract the portal ID."""
    url = f"https://{host}/careersection/{section}/jobsearch.ftl"
    try:
        page = client.get_text(url)
    except Exception:
        return None
    p = _TaleoPortalParser()
    p.feed(page)
    return p.portal_id


def fetch_taleo(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Oracle Taleo Enterprise Edition job listings.

    Source shape:
        source: {ats: taleo, host: "company.taleo.net", section: "2"}
    """
    host = src["host"]
    section = str(src.get("section", "2"))

    # Step 1: get the portal ID from the search page
    portal_id = src.get("portal_id") or _taleo_get_portal(client, host, section)
    if not portal_id:
        return []

    api = f"https://{host}/careersection/rest/jobboard/searchjobs"
    jobs: list[dict] = []
    page_num = 0
    while True:
        try:
            data = client.get_json(
                api,
                params={"lang": "en", "portal": portal_id, "start": page_num * 25},
            )
        except Exception:
            break
        req_list = data.get("reqList") or []
        columns = data.get("columnHeader") or []
        # Build column index map: find title, location, department cols
        col_map: dict[str, int] = {}
        for i, col in enumerate(columns):
            lbl = (col.get("display") or "").lower()
            if any(k in lbl for k in ("title", "position", "job title")):
                col_map.setdefault("title", i)
            elif any(k in lbl for k in ("location", "city")):
                col_map.setdefault("location", i)
            elif any(k in lbl for k in ("date", "posted")):
                col_map.setdefault("posted", i)
            elif any(k in lbl for k in ("department", "function")):
                col_map.setdefault("department", i)

        for req in req_list:
            cells = req.get("column") or []
            def _cell(idx: int | None) -> str:
                if idx is None or idx >= len(cells):
                    return ""
                return (cells[idx].get("value") or "").strip()

            # Taleo often gives title as req["title"] or via column
            title = req.get("title") or _cell(col_map.get("title"))
            if not title:
                continue
            req_id = str(req.get("jobId") or req.get("req") or "")
            location = _cell(col_map.get("location"))
            posted_raw = _cell(col_map.get("posted"))
            posted = parse_date(posted_raw)
            department = _cell(col_map.get("department"))
            job_url = f"https://{host}/careersection/{section}/jobdetail.ftl?job={req_id}"
            jobs.append({
                "source_id": req_id,
                "title": title.strip(),
                "url": job_url,
                "location": location,
                "posted_date": posted,
                "posted_estimated": posted is None,
                "department": department or None,
            })

        page_num += 1
        if not req_list or len(jobs) >= max_jobs:
            break
        total = data.get("pageInfo", {}).get("totalCount") or 0
        if total and len(jobs) >= total:
            break

    return jobs[:max_jobs]


# ------------------------------------------------------------------ iCIMS
def fetch_icims(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """iCIMS job listings.

    Tries three approaches in order:
    1. /api/jobs JSON endpoint — works for custom-domain iCIMS portals (e.g. careers.alaskaair.com).
    2. /jobs/search?ss=1&in_iframe=1 HTML listing — server-rendered pages on *.icims.com portals;
       paginates via searchPage=N until no new jobs appear.
    3. /sitemaps/index.xml sitemap — original fallback.

    Errors from each approach are collected and raised if all three return nothing,
    so verify_report.json shows the actual failure reason instead of silent zeros.

    Source shape:
        source: {ats: icims, url: "https://careers-example.icims.com"}
        source: {ats: icims, url: "https://careers.example.com"}
    """
    base = src["url"].rstrip("/")
    jobs: list[dict] = []
    errors: list[str] = []

    # ── Approach 1: JSON /api/jobs (custom-domain portals like careers.alaskaair.com) ──
    api_url = f"{base}/api/jobs"
    try:
        data = client.get_json(api_url)
        job_list = data if isinstance(data, list) else (
            data.get("jobs") or data.get("results") or data.get("data") or []
        )
        for j in job_list:
            title = j.get("title") or j.get("job_title") or j.get("name") or ""
            if not title:
                continue
            job_id = str(j.get("id") or j.get("job_id") or j.get("req_id") or "")
            url = j.get("canonicalUrl") or j.get("url") or j.get("apply_url") or f"{base}/jobs/{job_id}"
            location = (j.get("location") or j.get("city") or "")
            if isinstance(location, dict):
                location = location.get("name") or location.get("city") or ""
            country = (j.get("country") or j.get("country_code") or "")
            if isinstance(country, dict):
                country = country.get("code") or country.get("name") or ""
            posted = parse_date(j.get("date_posted") or j.get("posted_date") or j.get("created_date"))
            jobs.append({
                "source_id": job_id or url,
                "title": title.strip(),
                "url": url,
                "location": str(location),
                "country_code": str(country).upper() or None,
                "posted_date": posted,
                "posted_estimated": posted is None,
                "employment_type": j.get("job_type") or j.get("employment_type"),
                "department": j.get("department") or j.get("category"),
            })
        if jobs:
            return jobs[:max_jobs]
    except Exception as e:
        errors.append(f"api/jobs: {e}")

    # ── Approach 2: Server-rendered HTML at /jobs/search (*.icims.com hosted portals) ──
    # iCIMS renders job listings server-side at /jobs/search?ss=1&in_iframe=1.
    # Job title links follow: <a class="iCIMS_jobTitle" href="/jobs/ID/slug/job">Title</a>
    # Pagination: add &searchPage=N (stops when a page returns no new jobs).
    try:
        seen: set[str] = set()
        for page_num in range(1, 200):  # safety cap at 199 pages
            search_url = f"{base}/jobs/search?ss=1&in_iframe=1&searchPage={page_num}"
            html = client.get_text(search_url)

            # Primary pattern: href before class
            matches = re.findall(
                r'href="(/jobs/\d+/[^"]+/job)"[^>]*class="iCIMS_jobTitle"[^>]*>\s*([^<]+)',
                html,
            )
            # Secondary pattern: class before href
            if not matches:
                matches = re.findall(
                    r'class="iCIMS_jobTitle"[^>]*href="(/jobs/\d+/[^"]+/job)"[^>]*>\s*([^<]+)',
                    html,
                )
            # Tertiary: any /jobs/NNN/.../job link with visible label (no class required)
            if not matches:
                matches = re.findall(
                    r'href="(/jobs/\d+/[^"#"]+/job)"[^>]*>\s*([^<\n]{5,120})',
                    html,
                )

            new_on_page = 0
            for path, raw_title in matches:
                path = path.strip()
                title = raw_title.strip()
                if not path or not title or path in seen:
                    continue
                seen.add(path)
                job_url = f"{base}{path}" if path.startswith("/") else path
                m = re.search(r"/jobs/(\d+)/", path)
                jobs.append({
                    "source_id": m.group(1) if m else path,
                    "title": title,
                    "url": job_url,
                    "location": "",
                    "posted_estimated": True,
                    "needs_detail": True,
                    "detail_url": job_url,
                })
                new_on_page += 1
                if len(jobs) >= max_jobs:
                    break

            if new_on_page == 0:
                break  # Empty page → pagination complete
            if len(jobs) >= max_jobs:
                break

        if jobs:
            return jobs[:max_jobs]
    except Exception as e:
        errors.append(f"html_search: {e}")

    # ── Approach 3: Sitemap (original fallback) ──
    sitemap_url = f"{base}/sitemaps/index.xml"
    try:
        sitemap_xml = client.get_text(sitemap_url)
        urls = re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)
        sub_urls: list[str] = []
        for u in urls:
            if "sitemap" in u.lower() and u.endswith(".xml"):
                try:
                    sub = client.get_text(u)
                    sub_urls.extend(re.findall(r"<loc>([^<]+)</loc>", sub))
                except Exception:
                    pass
        all_urls = sub_urls or urls
        for url in all_urls:
            if "/jobs/" in url and url not in [j.get("url") for j in jobs]:
                m = re.search(r"/jobs/(\d+)", url)
                job_id = m.group(1) if m else url
                jobs.append({
                    "source_id": job_id,
                    "title": "",
                    "url": url,
                    "detail_url": url,
                    "needs_detail": True,
                    "posted_estimated": True,
                })
            if len(jobs) >= max_jobs:
                break
    except Exception as e:
        errors.append(f"sitemap: {e}")

    # Surface errors so verify_report.json shows the real failure, not silent zeros
    if not jobs and errors:
        raise Exception("; ".join(errors))

    return jobs[:max_jobs]


# ------------------------------------------------------------------ Phenom People (TXM)
def fetch_phenom(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Phenom People career sites via sitemap-based discovery.

    Source shape:
        source: {ats: phenom, url: "https://careers.example.com", country: "US"}

    Phenom's job search API requires OAuth. We use their sitemaps instead,
    which are allowed by robots.txt on all confirmed employers.
    """
    base = src["url"].rstrip("/")
    country_hint = src.get("country", "").upper()
    jobs: list[dict] = []
    seen: set[str] = set()

    # Phenom sitemaps: try multiple locale paths
    sitemap_candidates = [
        f"{base}/sitemap.xml",
        f"{base}/us/en/sitemap.xml",
        f"{base}/en/sitemap.xml",
        f"{base}/ca/en/sitemap.xml",
        f"{base}/in/en/sitemap.xml",
    ]

    job_urls: list[str] = []
    for sitemap_url in sitemap_candidates:
        try:
            xml = client.get_text(sitemap_url)
        except Exception:
            continue
        urls = re.findall(r"<loc>([^<]+)</loc>", xml)
        # Check if it's a sitemap index
        sub_sitemaps = [u for u in urls if "sitemap" in u.lower() and u.endswith(".xml")]
        if sub_sitemaps:
            for sub_url in sub_sitemaps:
                try:
                    sub = client.get_text(sub_url)
                    sub_urls = re.findall(r"<loc>([^<]+)</loc>", sub)
                    job_urls.extend(u for u in sub_urls if "/jobs/" in u or "/job/" in u)
                except Exception:
                    continue
        else:
            job_urls.extend(u for u in urls if "/jobs/" in u or "/job/" in u)

        if job_urls:
            break  # Found job URLs in this sitemap

    # De-duplicate
    for url in job_urls:
        url = url.split("?")[0]  # strip query params
        if url in seen:
            continue
        seen.add(url)
        # Extract job ID from URL
        m = re.search(r"/(?:jobs?|positions?)/(?:[^/]+/)?(\d+)", url)
        job_id = m.group(1) if m else url
        jobs.append({
            "source_id": job_id,
            "title": "",  # will be filled by detail fetch
            "url": url,
            "detail_url": url,
            "needs_detail": True,
            "country_code": country_hint or None,
            "posted_estimated": True,
        })
        if len(jobs) >= max_jobs:
            break

    return jobs[:max_jobs]


# ------------------------------------------------------------------ Breezy HR
def fetch_breezy(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Breezy HR via public JSON feed.

    Source shape:
        source: {ats: breezy, company: "embraer"}

    Breezy exposes a public /json endpoint for each company's open positions.
    No authentication required.
    """
    company = src["company"]
    url = f"https://{company}.breezy.hr/json"
    try:
        data = client.get_json(url)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    jobs: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        position_id = str(item.get("_id", "") or item.get("id", ""))
        if not position_id:
            continue
        slug = item.get("friendly_id") or item.get("id") or position_id
        job_url = f"https://{company}.breezy.hr/p/{slug}"
        # Location parsing
        loc_obj = item.get("location") or {}
        city = loc_obj.get("city", "") if isinstance(loc_obj, dict) else ""
        country_raw = (loc_obj.get("country", {}) or {}).get("id", "") if isinstance(loc_obj, dict) else ""
        location = city or ""
        country_code = country_raw.upper()[:2] if country_raw else None

        # Work type
        work_type = (item.get("type") or {}).get("name", "") if isinstance(item.get("type"), dict) else ""
        employment_type = None
        if work_type:
            wl = work_type.lower()
            if "full" in wl:
                employment_type = "full_time"
            elif "part" in wl:
                employment_type = "part_time"
            elif "contract" in wl:
                employment_type = "contract"

        jobs.append({
            "source_id": position_id,
            "title": item.get("name", ""),
            "url": job_url,
            "location": location,
            "country_code": country_code,
            "posted_date": None,
            "posted_estimated": False,
            "closing_date": None,
            "work_mode": None,
            "employment_type": employment_type,
        })
        if len(jobs) >= max_jobs:
            break

    return jobs[:max_jobs]


# ------------------------------------------------------------------ Gupy (Brazilian ATS)
def fetch_gupy(client: PoliteClient, src: dict, max_jobs: int = 3000) -> list[dict]:
    """Gupy ATS via public REST API.

    Source shape:
        source: {ats: gupy, company_id: "voeazul"}  # subdomain of gupy.io

    Gupy exposes a public pagination API with no auth for published positions.
    """
    company_id = src["company_id"]
    base_url = f"https://portal.api.gupy.io/api/v1/jobs"
    jobs: list[dict] = []
    page = 1

    while len(jobs) < max_jobs:
        try:
            data = client.get_json(base_url, params={
                "companyId": company_id,
                "isRemoteWork": "false",
                "limit": 100,
                "offset": (page - 1) * 100,
            })
        except Exception:
            break

        items = data if isinstance(data, list) else (data.get("data") or data.get("jobs") or [])
        if not items:
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("id", ""))
            if not job_id:
                continue
            job_url = item.get("jobUrl") or f"https://{company_id}.gupy.io/job/{job_id}"
            location_parts = []
            city = item.get("city") or ""
            state = item.get("state") or ""
            if city:
                location_parts.append(city)
            if state and state != city:
                location_parts.append(state)
            location = ", ".join(location_parts)
            # Gupy is Brazil-based; default BR unless specified
            country_code = src.get("country", "BR").upper()

            work_type = (item.get("type") or "").lower()
            employment_type = None
            if "effective" in work_type or "full" in work_type or "clt" in work_type:
                employment_type = "full_time"
            elif "part" in work_type:
                employment_type = "part_time"
            elif "intern" in work_type or "estagi" in work_type:
                employment_type = "internship"

            jobs.append({
                "source_id": job_id,
                "title": item.get("name", ""),
                "url": job_url,
                "location": location,
                "country_code": country_code,
                "posted_date": item.get("publishedDate"),
                "posted_estimated": False,
                "closing_date": item.get("applicationDeadline"),
                "work_mode": None,
                "employment_type": employment_type,
            })
            if len(jobs) >= max_jobs:
                break

        if len(items) < 100:
            break  # Last page
        page += 1

    return jobs[:max_jobs]


CONNECTORS = {
    "workday": (fetch_workday, workday_detail),
    "greenhouse": (fetch_greenhouse, None),
    "lever": (fetch_lever, None),
    "smartrecruiters": (fetch_smartrecruiters, None),
    "jsonld": (fetch_jsonld, jsonld_detail),
    "oracle": (fetch_oracle, None),
    "successfactors": (fetch_successfactors, None),
    "taleo": (fetch_taleo, None),
    "icims": (fetch_icims, jsonld_detail),
    "phenom": (fetch_phenom, jsonld_detail),
    "breezy": (fetch_breezy, None),
    "gupy": (fetch_gupy, None),
}
