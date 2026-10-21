import datetime as dt

from fetcher import connectors as c
from fetcher.geo import country_from_location, region_of
from fetcher.roles import classify_title, detect_work_mode, is_aviation_job
from fetcher.common import today
from fetcher.run import merge_employer_jobs, purge_expired, is_visible, fetch_pending_details


class FakeClient:
    """Answers requests from a dict of url -> response, records what was asked."""
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def _get(self, url):
        self.calls.append(url)
        for key, value in self.responses.items():
            if url.startswith(key):
                return value(url) if callable(value) else value
        raise AssertionError(f"unexpected url {url}")

    def get_json(self, url, params=None, **kw):
        return self._get(url)

    def get_text(self, url):
        return self._get(url)

    def post_json(self, url, payload):
        self.calls.append((url, payload))
        # Strip query string for lookup so Taleo URLs (?lang=en&portal=...) match
        base_url = url.split("?")[0]
        responses = self.responses.get(url) or self.responses.get(base_url)
        if responses is None:
            raise AssertionError(f"unexpected url {url}")
        # Oracle connector pages by offset; Taleo by pageNo (1-indexed)
        if "offset" in payload:
            idx = payload["offset"] // 20
        elif "pageNo" in payload:
            idx = payload["pageNo"] - 1
        else:
            idx = 0
        return responses[idx] if isinstance(responses, list) else responses


# ---------------------------------------------------------------- roles
def test_roles():
    cases = {
        "First Officer A320": "pilots",
        "Captain - Boeing 777": "pilots",
        "Cabin Crew - Dubai Based": "cabin-crew",
        "Flight Attendant (Bilingual)": "cabin-crew",
        "B1 Licensed Aircraft Engineer": "engineering-maintenance",
        "Avionics Technician": "engineering-maintenance",
        "IT Support Technician": "corporate",
        "Ramp Agent": "ground-operations",
        "Baggage Handler": "ground-operations",
        "Flight Dispatcher": "flight-operations",
        "Air Traffic Control Officer": "flight-operations",
        "Cargo Sales Executive": "cargo-logistics",
        "Customer Service Agent": "customer-service-sales",
        "Senior Software Engineer": "corporate",
        "Financial Controller": "corporate",
        "Trampoline instructor": None,
    }
    for title, role in cases.items():
        assert classify_title(title) == role, title
    assert classify_title("Systems Engineer", "manufacturer") == "engineering-maintenance"
    assert classify_title("Systems Engineer", "airline") == "corporate"


def test_work_mode():
    assert detect_work_mode("Data Analyst (Hybrid)") == "Hybrid"
    assert detect_work_mode("Recruiter", "Remote - UK") == "Remote"
    assert detect_work_mode("Ramp Agent", "London") == "On-site"
    assert detect_work_mode("x", structured="onsite") == "On-site"
    assert detect_work_mode("x", structured="Remote") == "Remote"


# ---------------------------------------------------------------- geography
def test_countries():
    assert country_from_location("Seattle, WA") == "US"
    assert country_from_location("San Jose, CA") == "US"
    assert country_from_location("Toronto, ON, CA") == "CA"
    assert country_from_location("Dubai - United Arab Emirates") == "AE"
    assert country_from_location("London, United Kingdom") == "GB"
    assert country_from_location("Doha") == "QA"
    assert country_from_location("Bengaluru, India") == "IN"
    assert country_from_location("Hamburg, DEU") == "DE"
    assert country_from_location("UAE") == "AE"
    assert country_from_location("") is None
    assert region_of("AE") == "Middle East" and region_of("BR") == "Latin America and Caribbean"


# ---------------------------------------------------------------- connectors
def test_posted_on():
    base = dt.date(2026, 10, 4)
    assert c.posted_on_to_date("Posted Today", base) == ("2026-10-04", False)
    assert c.posted_on_to_date("Posted Yesterday", base) == ("2026-10-03", False)
    assert c.posted_on_to_date("Posted 5 Days Ago", base) == ("2026-09-29", False)
    assert c.posted_on_to_date("Posted 30+ Days Ago", base) == ("2026-09-04", True)


def test_workday_paging_and_detail():
    api = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers/jobs"
    page = lambda n, total: {"total": total, "jobPostings": [
        {"title": f"Job {n}-{i}", "externalPath": f"/job/X/{n}-{i}", "locationsText": "Hamburg, Germany",
         "postedOn": "Posted Today"} for i in range(20 if n == 0 else 5)]}
    client = FakeClient({api: [page(0, 25), page(1, 0)]})
    jobs = c.fetch_workday(client, {"url": "https://acme.wd3.myworkdayjobs.com/en-US/Careers"})
    assert len(jobs) == 25
    assert jobs[0]["url"] == "https://acme.wd3.myworkdayjobs.com/Careers/job/X/0-0"
    detail_client = FakeClient({"https://acme.wd3": {"jobPostingInfo": {
        "country": {"descriptor": "Germany"}, "startDate": "2026-09-30", "remoteType": "Hybrid",
        "timeType": "Full time", "jobDescription": "<p>long text we never keep</p>"}}})
    d = c.workday_detail(detail_client, jobs[0])
    assert d["country_code"] == "DE" and d["posted_date"] == "2026-09-30" and d["work_mode"] == "Hybrid"
    assert "jobDescription" not in d and "long text" not in str(d)


def test_lever_greenhouse_smartrecruiters():
    lever = FakeClient({"https://api.lever.co/v0/postings/acme": [
        {"id": "a1", "text": "Pilot", "hostedUrl": "https://jobs.lever.co/acme/a1", "createdAt": 1790000000000,
         "categories": {"location": "Auckland", "commitment": "Full-time"}, "workplaceType": "onsite", "country": "NZ"}]})
    j = c.fetch_lever(lever, {"company": "acme"})[0]
    assert j["country_code"] == "NZ" and j["posted_date"].startswith("2026")

    gh = FakeClient({"https://boards-api.greenhouse.io/v1/boards/acme/jobs": {"jobs": [
        {"id": 7, "title": "Ramp Agent", "absolute_url": "https://x/7", "location": {"name": "Denver, CO"},
         "first_published": "2026-10-01T10:00:00Z"}]}})
    assert c.fetch_greenhouse(gh, {"board": "acme"})[0]["posted_date"] == "2026-10-01"

    sr = FakeClient({"https://api.smartrecruiters.com/v1/companies/Acme/postings": {"totalFound": 1, "content": [
        {"id": "9", "name": "Cabin Crew", "releasedDate": "2026-09-20T00:00:00.000Z",
         "location": {"city": "Doha", "country": "qa", "remote": False}}]}})
    j = c.fetch_smartrecruiters(sr, {"company": "Acme"})[0]
    assert j["country_code"] == "QA" and j["url"].endswith("/Acme/9")


def test_jsonld():
    page = """<html><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
      {"@type":"JobPosting","title":"Aircraft Mechanic","datePosted":"2026-09-01","validThrough":"2026-11-01",
       "identifier":{"value":"R-55"},"employmentType":["FULL_TIME"],
       "jobLocation":{"@type":"Place","address":{"addressLocality":"Toulouse","addressCountry":"FR"}}}]}
    </script></html>"""
    raws = c.fetch_jsonld(FakeClient({"https://careers.example.com": page}), {"listing_url": "https://careers.example.com/jobs"})
    assert raws[0]["source_id"] == "R-55" and raws[0]["country_code"] == "FR" and raws[0]["closing_date"] == "2026-11-01"

    listing = '<a href="/job/1">One</a><a href="/job/2#apply">Two</a><a href="/about">x</a>'
    links = c.fetch_jsonld(FakeClient({"https://careers.example.com": listing}),
                           {"listing_url": "https://careers.example.com/jobs", "job_link_pattern": "/job/"})
    assert [l["url"] for l in links] == ["https://careers.example.com/job/1", "https://careers.example.com/job/2"]


# ---------------------------------------------------------------- store logic
def test_merge_expire_and_return():
    emp = {"name": "Example Air", "slug": "example-air", "type": "airline"}
    jobs = {}
    raws = [{"source_id": "1", "title": "First Officer", "url": "https://example.com/j/1", "location": "Dubai"},
            {"source_id": "2", "title": "Ramp Agent", "url": "https://example.com/j/2", "location": "Doha"}]
    new = merge_employer_jobs(jobs, emp, raws, "2026-10-01")
    assert len(new) == 2
    rec = next(r for r in jobs.values() if r["title"] == "First Officer")
    assert rec["country_code"] == "AE" and rec["role"] == "pilots" and rec["posted_estimated"]
    assert is_visible(rec)

    merge_employer_jobs(jobs, emp, raws[:1], "2026-10-02")           # job 2 missing once
    j2 = next(r for r in jobs.values() if r["title"] == "Ramp Agent")
    assert j2["status"] == "active" and j2["missed_runs"] == 1
    merge_employer_jobs(jobs, emp, raws[:1], "2026-10-03")           # missing twice -> expired
    assert j2["status"] == "expired"
    merge_employer_jobs(jobs, emp, raws, "2026-10-04")               # back again -> active
    assert j2["status"] == "active" and j2["missed_runs"] == 0

    merge_employer_jobs(jobs, emp, [], "2026-10-05")
    merge_employer_jobs(jobs, emp, [], "2026-10-06")
    assert all(r["status"] == "expired" for r in jobs.values())
    assert purge_expired(jobs, 30, "2026-11-30") == 2 and not jobs


def test_pending_details_retry_instead_of_giving_up_once():
    """A real bug: Cathay Pacific/Southwest/United/Air Canada were each missing titles
    on roughly half their jobs. Root cause: a detail fetch that succeeded but came back
    with no usable title (bot-mitigation page, cold CDN cache, etc. - confirmed live,
    the real job pages DO have the title) permanently cleared detail_pending, so that
    job's title was never tried again. fetch_pending_details() must instead keep a job
    pending and retry it on later calls, giving up only after max_detail_attempts."""
    emp = {"name": "Example Air", "slug": "example-air", "type": "airline", "country": "US"}
    jobs = {}
    merge_employer_jobs(jobs, emp, [{"source_id": "1", "title": "", "url": "https://careers.example.com/job/1",
                                      "detail_url": "https://careers.example.com/job/1"}], "2026-10-01")
    rec = next(iter(jobs.values()))
    assert rec["detail_pending"] is True

    attempts = {"n": 0}
    def flaky_detail(client, r):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return {}  # looks like a successful fetch, but no usable title this time
        return {"title": "First Officer", "location": "Doha, Qatar",
                "posted_date": "2026-10-01", "posted_estimated": False}

    for _ in range(2):  # two runs with an empty-but-successful fetch: stays pending
        filled, empty, left = fetch_pending_details(FakeClient({}), jobs, emp, flaky_detail)
        assert filled == 0 and empty == 1
        assert rec.get("detail_pending") is True and not rec.get("title")

    # third run: the detail page finally has a title -> filled in and no longer pending
    filled, empty, left = fetch_pending_details(FakeClient({}), jobs, emp, flaky_detail)
    assert filled == 1 and empty == 0
    assert rec["title"] == "First Officer"
    assert "detail_pending" not in rec and "detail_attempts" not in rec
    assert is_visible(rec)


def test_pending_details_give_up_after_max_attempts():
    """A job whose detail page never has a title (genuinely gone, not a hiccup) must
    stop being retried eventually, so a permanently-broken listing doesn't burn a fetch
    on every single run forever."""
    emp = {"name": "Example Air", "slug": "example-air", "type": "airline", "country": "US"}
    jobs = {}
    merge_employer_jobs(jobs, emp, [{"source_id": "1", "title": "", "url": "https://careers.example.com/job/1",
                                      "detail_url": "https://careers.example.com/job/1"}], "2026-10-01")
    rec = next(iter(jobs.values()))

    calls = {"n": 0}
    def always_empty(client, r):
        calls["n"] += 1
        return {}

    for _ in range(3):
        fetch_pending_details(FakeClient({}), jobs, emp, always_empty, max_detail_attempts=3)
    assert "detail_pending" not in rec  # gave up after 3 attempts
    assert calls["n"] == 3

    # a later run must not fetch it again - it's no longer pending
    fetch_pending_details(FakeClient({}), jobs, emp, always_empty, max_detail_attempts=3)
    assert calls["n"] == 3


def test_closing_date_before_posted_date_is_dropped_not_shown():
    """Two real bugs, found on live Workday listings. (1) Rolls-Royce: the site showed
    'Closes 6 October' under 'Posted 19 October', while Rolls-Royce's own careers page
    for the same job said the real closing date was 22 October - the live Workday API
    had no endDate/closing-date field at all for that job, our stored value was a stale
    leftover from an earlier fetch that never got cleared when a later fetch (e.g.
    after a repost) stopped providing one. (2) Boeing: a stored closing date identical
    to the posting date, while the live API already showed a later, real closing date -
    Workday appears to start some requisitions with endDate == startDate as a
    placeholder before HR sets a real deadline. Both cases must be dropped, not shown."""
    emp = {"name": "Example Air", "slug": "example-air", "type": "manufacturer", "country": "US"}
    d = today()
    fmt = lambda delta: (d + dt.timedelta(days=delta)).isoformat()

    jobs = {}
    merge_employer_jobs(jobs, emp, [{"source_id": "1", "title": "Overhaul Engineer",
                                      "url": "https://careers.example.com/job/1",
                                      "posted_date": fmt(-20), "closing_date": fmt(-5)}], fmt(-20))
    rec = next(iter(jobs.values()))
    # repost: a new, later posted_date, and this time no closing_date at all
    merge_employer_jobs(jobs, emp, [{"source_id": "1", "title": "Overhaul Engineer",
                                      "url": "https://careers.example.com/job/1",
                                      "posted_date": fmt(-1), "posted_estimated": False}], fmt(0))
    assert rec["posted_date"] == fmt(-1)
    assert rec.get("closing_date") is None, "stale closing_date from before the repost must be dropped"

    # closing_date before posted_date in a single fetch is dropped outright
    jobs2 = {}
    merge_employer_jobs(jobs2, emp, [{"source_id": "2", "title": "Pilot",
                                       "url": "https://careers.example.com/job/2",
                                       "posted_date": fmt(-1), "closing_date": fmt(-15)}], fmt(0))
    assert next(iter(jobs2.values())).get("closing_date") is None

    # closing_date identical to posted_date (the Boeing placeholder pattern) is dropped
    jobs4 = {}
    merge_employer_jobs(jobs4, emp, [{"source_id": "4", "title": "RF Sensors Engineer",
                                       "url": "https://careers.example.com/job/4",
                                       "posted_date": fmt(-5), "closing_date": fmt(-5)}], fmt(0))
    assert next(iter(jobs4.values())).get("closing_date") is None

    # a sensible, future closing date after the posting date is kept
    jobs3 = {}
    merge_employer_jobs(jobs3, emp, [{"source_id": "3", "title": "Engineer",
                                       "url": "https://careers.example.com/job/3",
                                       "posted_date": fmt(-1), "closing_date": fmt(2)}], fmt(0))
    assert next(iter(jobs3.values())).get("closing_date") == fmt(2)


def test_only_web_links_are_allowed():
    from fetcher.common import safe_url
    assert safe_url("https://careers.example.com/job/1") == "https://careers.example.com/job/1"
    for bad in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "//evil.com",
                "https://", "https://exa mple.com", 'https://a.com/"onmouseover', None, 42):
        assert safe_url(bad) is None, bad
    emp = {"name": "Example Air", "slug": "example-air", "type": "airline"}
    jobs = {}
    merge_employer_jobs(jobs, emp, [{"source_id": "x", "title": "Pilot", "url": "javascript:alert(1)"}], "2026-10-01")
    assert not any(is_visible(r) for r in jobs.values())


def test_oracle_connector():
    host = "abcd.fa.ocs.oraclecloud.com"
    def page(url):
        off = int(url.split("offset=")[1].split(",")[0])
        reqs = [{"Id": f"{off + i}", "Title": f"Job {off + i}", "PostedDate": "2026-10-01",
                 "PrimaryLocation": "London, England, United Kingdom", "PrimaryLocationCountry": "GB",
                 "WorkplaceType": "Hybrid"} for i in range(25 if off == 0 else 5)]
        return {"items": [{"TotalJobsCount": 30, "requisitionList": reqs}]}
    client = FakeClient({f"https://{host}/hcmRestApi": page})
    jobs = c.fetch_oracle(client, {"host": host, "site": "CX_1"})
    assert len(jobs) == 30 and jobs[0]["country_code"] == "GB" and jobs[0]["work_mode"] == "hybrid"
    assert jobs[0]["url"] == f"https://{host}/hcmUI/CandidateExperience/en/sites/CX_1/job/0"


def test_jsonld_listing_pagination():
    pages = {0: '<a href="/jobs/1/a/job">1</a><a href="/jobs/2/b/job">2</a>',
             1: '<a href="/jobs/3/c/job">3</a>', 2: '<a href="/jobs/3/c/job">3</a>'}
    client = FakeClient({"https://x.icims.com/jobs/search": lambda u: pages[int(u.split("pr=")[1].split("&")[0])]})
    links = c.list_job_links(client, {"listing_url": "https://x.icims.com/jobs/search?pr={page}&in_iframe=1",
                                       "job_link_pattern": r"/jobs/\d+/", "max_pages": 10})
    assert [l.split("/jobs/")[1][0] for l in links] == ["1", "2", "3"]


def test_countries_from_company_location_styles():
    assert country_from_location("US-GA-MIDLAND-MPC ~ 8801 Macon Rd", "US") == "US"
    assert country_from_location("CA-QC-LONGUEUIL-J01 ~ 1000 Blvd Marie-Victorin", "US") == "CA"
    assert country_from_location("Toulouse Area", "FR") == "FR"
    assert country_from_location("Lisbon (Airbus Portugal)", "FR") == "PT"
    assert country_from_location("Friedrichshafen", "GB") == "DE"
    assert country_from_location("Lynn", "US") == "US"
    assert country_from_location("Remote") is None


def test_roles_in_other_languages_and_manufacturing():
    assert classify_title("Servicetekniker") == "engineering-maintenance"
    assert classify_title("CNC-Rundschleifer (m/f/d)") == "engineering-maintenance"
    assert classify_title("Ingénieur Recherche & Technologique") == "engineering-maintenance"
    assert classify_title("Softwareentwickler (m/w/d)") == "corporate"


def test_clean_coded_locations():
    from fetcher.geo import clean_location
    assert clean_location("IN-KA-BENGALURU-BLDG 1 ~ Hitech, Defence & Aerospace Park ~ HI TECH DEFENSE") == "Bengaluru, India"
    assert clean_location("PL-30-KALISZ-140 ~ Czestochowska 140 ~ CZESTOCHOWSKA") == "Kalisz, Poland"
    assert clean_location("US-CT-EAST HARTFORD-ETC ~ 400 Main St ~ BLDG ETC") == "East Hartford, United States"
    assert clean_location("US-AZ-TUCSON-801 ~ 1151 E Hermans Rd ~ BLDG 801 (External Site)") == "Tucson, United States"
    assert clean_location("Toulouse Area") == "Toulouse Area"
    assert clean_location("Seattle, WA") == "Seattle, WA"


def test_successfactors_connector():
    base = "https://careers.example-air.com"
    # Realistic SF HTML: cells contain repeated title, whitespace, location, job IDs
    listing_html = """<html><body>
    <div>Results 1 &ndash; 25 of 30 jobs</div>
    <table>
      <tr><th>Title</th><th>Location</th></tr>
      <tr><td><a href="/job/Dubai-First-Officer-A380/12345/">First Officer A380</a>
          </td><td>First Officer A380
                    First Officer A380
              Dubai, AE, 12345
              58082</td></tr>
      <tr><td><a href="/job/London-Cabin-Crew-E1-1AB/67890/">Cabin Crew</a>
          </td><td>Cabin Crew
                    Cabin Crew
              London, United Kingdom
              58090</td></tr>
    </table></body></html>"""
    page2_html = """<html><body>
    <table>
      <tr><td><a href="/cag/job/Singapore-Ramp-Agent-S123/11111/">Ramp Agent</a>
          </td><td>Ramp Agent
              Operations
              5 Oct 2026</td></tr>
    </table></body></html>"""
    def page(url):
        if "startrow=25" in url:
            return page2_html
        return listing_html
    client = FakeClient({base: page})
    jobs = c.fetch_successfactors(client, {"url": base})
    assert len(jobs) == 3
    assert jobs[0]["source_id"] == "12345"
    assert jobs[0]["title"] == "First Officer A380"
    assert jobs[0]["url"] == f"{base}/job/Dubai-First-Officer-A380/12345/"
    assert jobs[0]["location"] == "Dubai, AE, 12345"   # cleaned from messy cell
    assert jobs[1]["source_id"] == "67890"
    assert jobs[1]["location"] == "London, United Kingdom"
    # third job uses /unit/job/ URL pattern (Changi-style); location falls back to dept
    assert jobs[2]["source_id"] == "11111"
    assert jobs[2]["url"] == f"{base}/cag/job/Singapore-Ramp-Agent-S123/11111/"
    assert jobs[2]["location"] == "Operations"  # no comma-line, falls back to first remaining


def test_aviation_filter_blocks_non_aviation():
    """Non-aviation titles from conglomerates are excluded."""
    blocked = [
        "Building Automation Engineer",
        "Lead HVAC Controls Technician",
        "Lead Field Service Technician | Fire Alarm Systems",
        "Key Account Manager Security & Access Solutions (m/f/d) Building Automation",
        "Chemical Engineer II",
        "Chemical Engr I",
        "Advanced Field Service Engineer ( O&G Metering Specialist)",
        "Advanced Field Service Engineer - DCS Process Automation",
        "Shipboard Missiles Critical Munitions Associate Director",
        "Associate Director of Business Development Undersea Programs (Hybrid)",
        "Senior Manager, Defense Hardware Technology- Active Secret (Onsite)",
        "Lead Building Automation Systems (BAS) Technician",
        "Field Service Engineer - HVAC m/f/d",
        "Major Project Sales Executive-Building Management Systems (Mid-Atlantic)",
    ]
    for title in blocked:
        assert not is_aviation_job(title), f"Should be blocked: {title}"


def test_aviation_filter_keeps_aviation_jobs():
    """Legitimate aviation titles pass through even with generic wording."""
    allowed = [
        "Software Engineer",
        "Advanced Project Engineer",
        "Account Manager II",
        "Senior Data Analyst",
        "Manufacturing Engineer II",
        "Quality Inspector",
        "Test Technician",
        "Mechanical Design Engineer",
        "Avionics Electronics Technician - 2nd Shift (Onsite)",
        "Aerospace Engineer - Propulsion",
        "Aircraft Maintenance Technician",
        "Cabin Crew",
        "First Officer A320",
        "Aerothermal Engineer Co-Op (January 2027) (Hybrid)",
        "Engine Overhaul Specialist",
        "Flight Test Engineer",
    ]
    for title in allowed:
        assert is_aviation_job(title), f"Should be allowed: {title}"


def test_aviation_filter_override():
    """A title with both non-aviation and aviation keywords is kept."""
    assert is_aviation_job("Aerospace Fire Detection Systems Engineer")
    assert is_aviation_job("Aircraft Chemical Process Technician")


# ---------------------------------------------------------------- new connectors
def test_taleo_connector():
    """Taleo fetches jobs using portal ID + reqList columns."""
    host = "example.taleo.net"
    portal_html = '<script>var cfg = {portal: "42", section: 2};</script>'
    api_resp = {
        "pageInfo": {"totalCount": 2},
        "columnHeader": [
            {"display": "Job Title"},
            {"display": "Location"},
            {"display": "Posted Date"},
        ],
        "reqList": [
            {"jobId": "REQ001", "title": "First Officer", "column": [
                {"value": "First Officer"},
                {"value": "Doha, Qatar"},
                {"value": "2026-09-15"},
            ]},
            {"jobId": "REQ002", "title": "Cabin Crew", "column": [
                {"value": "Cabin Crew"},
                {"value": "Dubai, UAE"},
                {"value": "2026-09-20"},
            ]},
        ],
    }
    client = FakeClient({
        f"https://{host}/careersection/2/jobsearch.ftl": portal_html,
        f"https://{host}/careersection/rest/jobboard/searchjobs": api_resp,
    })
    jobs = c.fetch_taleo(client, {"host": host})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "REQ001"
    assert jobs[0]["title"] == "First Officer"
    assert jobs[0]["location"] == "Doha, Qatar"
    assert "taleo.net" in jobs[0]["url"]
    assert jobs[1]["source_id"] == "REQ002"


def test_avature_connector():
    """Avature listing pages: one <article> per job, fields as labelled spans."""
    base = "https://careers.example-air.com/global/SearchJobs"

    def card(article_num, href, title, job_id, location, posted, closing=None):
        closing_span = (f'<span class="paragraph paragraph--inline">Closing date: {closing}</span>'
                         if closing else "")
        return f"""
        <article id="article--{article_num}">
          <div class="article__header"><div class="article__header__text">
            <h3 class="article__header__text__title title title--h3">
              <a class="link" href="{href}">{title}</a>
            </h3>
          </div></div>
          <div class="article__content">
            <span class="paragraph paragraph--inline">ID: {job_id}</span>
            <span class="paragraph paragraph--inline">Work locations: {location}</span>
            <span class="paragraph paragraph--inline">Posting date: {posted}</span>
            {closing_span}
          </div>
        </article>"""

    page0 = "<html><body>" + card(
        1, f"{base}/JobDetail/Wroclaw-Poland-Agent/62533", "Wroclaw, Poland | Agent",
        "2600008R", "Poland - Wroclaw", "03-07-2026", "31-12-2027",
    ) + card(
        2, f"{base}/JobDetail/Doha-Qatar-Cabin-Crew/70001", "Doha, Qatar | Cabin Crew",
        "2700001Q", "Qatar - Doha", "01-01-2026",
    ) + "</body></html>"
    page1 = "<html><body>" + card(
        1, f"{base}/JobDetail/London-UK-Pilot/80002", "London, UK | Pilot",
        "2800002P", "United Kingdom - London", "05-05-2026",
    ) + "</body></html>"  # fewer than page_size -> last page

    def responder(url):
        return page1 if "jobOffset=2" in url else page0

    client = FakeClient({base: responder})
    jobs = c.fetch_avature(client, {"url": base, "page_size": 2})
    assert len(jobs) == 3
    assert jobs[0]["source_id"] == "62533"
    assert jobs[0]["title"] == "Wroclaw, Poland | Agent"
    assert jobs[0]["location"] == "Wroclaw, Poland"
    assert jobs[0]["posted_date"] == "2026-07-03"
    assert jobs[0]["closing_date"] == "2027-12-31"
    assert jobs[0]["posted_estimated"] is False
    assert jobs[1]["source_id"] == "70001"
    assert jobs[1]["closing_date"] is None
    assert jobs[2]["source_id"] == "80002"
    assert jobs[2]["location"] == "London, United Kingdom"


def test_avature_connector_ignores_requested_page_size():
    """A real bug: Qatar Airways' Avature site ignores jobRecordsPerPage and always
    serves its own fixed batch of 6 jobs per page, so comparing the returned count
    against the *requested* page_size made fetch_avature stop after page 1 (saving
    only 6 of ~186 real jobs). It must instead keep paging - using the real batch
    size to advance the offset - until a page repeats jobs already seen."""
    base = "https://careers.example-air.com/global/SearchJobs"
    SITE_BATCH = 2  # the site's own fixed batch size, unrelated to page_size below

    def card(n, href, title):
        return f"""
        <article id="article--{n}">
          <div class="article__header"><div class="article__header__text">
            <h3 class="article__header__text__title title title--h3">
              <a class="link" href="{href}">{title}</a>
            </h3>
          </div></div>
          <div class="article__content">
            <span class="paragraph paragraph--inline">ID: J{n}</span>
            <span class="paragraph paragraph--inline">Work locations: Qatar - Doha</span>
            <span class="paragraph paragraph--inline">Posting date: 01-01-2026</span>
          </div>
        </article>"""

    all_jobs = [
        (1, f"{base}/JobDetail/a/1", "Job A"), (2, f"{base}/JobDetail/b/2", "Job B"),
        (3, f"{base}/JobDetail/c/3", "Job C"), (4, f"{base}/JobDetail/d/4", "Job D"),
        (5, f"{base}/JobDetail/e/5", "Job E"),
    ]

    def responder(url):
        offset = int(url.split("jobOffset=")[1].split("&")[0])
        batch = all_jobs[offset:offset + SITE_BATCH]  # ignores the requested page_size
        if not batch:
            return "<html><body></body></html>"
        return "<html><body>" + "".join(card(n, href, title) for n, href, title in batch) + "</body></html>"

    client = FakeClient({base: responder})
    jobs = c.fetch_avature(client, {"url": base, "page_size": 25})  # requested size the site ignores
    assert len(jobs) == 5, f"expected all 5 jobs, got {len(jobs)}"
    assert [j["source_id"] for j in jobs] == ["1", "2", "3", "4", "5"]


def test_icims_connector_json_api():
    """iCIMS connector uses /api/jobs JSON when available."""
    base = "https://careers.alaskaair.com"
    api_data = [
        {"id": "12345", "title": "Pilot", "location": "Seattle, WA", "country_code": "US",
         "date_posted": "2026-10-01", "apply_url": f"{base}/jobs/12345"},
        {"id": "67890", "title": "Ramp Agent", "location": "Anchorage, AK", "country_code": "US",
         "date_posted": "2026-10-02", "apply_url": f"{base}/jobs/67890"},
    ]
    client = FakeClient({f"{base}/api/jobs": api_data})
    jobs = c.fetch_icims(client, {"url": base})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "12345"
    assert jobs[0]["title"] == "Pilot"
    assert jobs[0]["country_code"] == "US"
    assert jobs[0]["posted_date"] == "2026-10-01"


def test_icims_connector_html_listing():
    """iCIMS connector falls back to HTML listing for *.icims.com hosted portals.

    Real portal structure (observed on careers-vistaglobal.icims.com):
      <a class="iCIMS_Anchor" href="/jobs/ID/slug/job?in_iframe=1">
        <span class="sr-only">Title</span><h3>Job Title Here</h3>
      </a>
    Pagination uses ?pr=N (not searchPage); stops on empty page.
    """
    base = "https://careers-jobyaviation.icims.com"

    page1_html = """<html><body>
    <a class="iCIMS_Anchor" href="/jobs/1001/avionics-engineer/job?in_iframe=1" title="1001 - Avionics Engineer">
      <span class="sr-only field-label">Title</span><h3>Avionics Engineer</h3>
    </a>
    <a class="iCIMS_Anchor" href="/jobs/1002/flight-operations-manager/job?in_iframe=1" title="1002 - Flight Ops">
      <span class="sr-only field-label">Title</span><h3>Flight Operations Manager</h3>
    </a>
    <a href="/jobs/search?pr=1&amp;in_iframe=1">Next page of results</a>
    </body></html>"""
    page2_html = "<html><body><p>No jobs found.</p></body></html>"

    client = FakeClient({
        f"{base}/api/jobs": lambda _: (_ for _ in ()).throw(Exception("404 Not Found")),
        f"{base}/jobs/search?ss=1&in_iframe=1": page1_html,
        f"{base}/jobs/search?pr=1&in_iframe=1": page2_html,
    })
    jobs = c.fetch_icims(client, {"url": base})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "1001"
    assert jobs[0]["title"] == "Avionics Engineer"
    assert jobs[0]["url"] == f"{base}/jobs/1001/avionics-engineer/job"
    assert jobs[1]["source_id"] == "1002"
    assert jobs[1]["title"] == "Flight Operations Manager"
    assert jobs[0]["needs_detail"] is True


def test_phenom_connector_sitemap():
    """Phenom connector discovers jobs via sitemap XML."""
    base = "https://careers.southwestair.com"
    sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex>
      <sitemap><loc>https://careers.southwestair.com/us/en/sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    jobs_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset>
      <url><loc>https://careers.southwestair.com/us/en/job/Flight-Attendant/12345</loc></url>
      <url><loc>https://careers.southwestair.com/us/en/job/First-Officer/67890</loc></url>
      <url><loc>https://careers.southwestair.com/us/en/home</loc></url>
    </urlset>"""
    client = FakeClient({
        f"{base}/sitemap.xml": sitemap_index,
        f"{base}/us/en/sitemap.xml": jobs_sitemap,
    })
    jobs = c.fetch_phenom(client, {"url": base, "country": "US"})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "12345"
    assert jobs[0]["country_code"] == "US"
    assert jobs[0]["needs_detail"] is True
    assert "12345" in jobs[0]["url"]


def test_breezy_connector():
    """Breezy HR connector fetches from public /json endpoint."""
    company = "embraer"
    api_data = [
        {
            "_id": "abc123",
            "friendly_id": "senior-avionics-engineer",
            "name": "Senior Avionics Engineer",
            "location": {"city": "Melbourne, FL", "country": {"id": "us"}},
            "type": {"name": "Full-Time"},
        },
        {
            "_id": "def456",
            "friendly_id": "flight-test-engineer",
            "name": "Flight Test Engineer",
            "location": {"city": "Gavião Peixoto", "country": {"id": "br"}},
            "type": {"name": "Full-Time"},
        },
    ]
    client = FakeClient({f"https://{company}.breezy.hr/json": api_data})
    jobs = c.fetch_breezy(client, {"company": company})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "abc123"
    assert jobs[0]["title"] == "Senior Avionics Engineer"
    assert jobs[0]["location"] == "Melbourne, FL"
    assert jobs[0]["country_code"] == "US"
    assert jobs[0]["employment_type"] == "full_time"
    assert "embraer.breezy.hr/p/senior-avionics-engineer" in jobs[0]["url"]
    assert jobs[1]["country_code"] == "BR"


def test_gupy_connector():
    """Gupy connector fetches from public REST API with pagination."""
    company_id = "voeazul"
    page1 = {
        "data": [
            {
                "id": 11111,
                "name": "Comandante A320",
                "city": "Campinas",
                "state": "SP",
                "jobUrl": "https://voeazul.gupy.io/job/11111",
                "publishedDate": "2026-10-01",
                "type": "effective",
            },
            {
                "id": 22222,
                "name": "Agente de Rampa",
                "city": "São Paulo",
                "state": "SP",
                "jobUrl": "https://voeazul.gupy.io/job/22222",
                "publishedDate": "2026-10-02",
                "type": "effective",
            },
        ]
    }
    client = FakeClient({"https://portal.api.gupy.io/api/v1/jobs": page1})
    jobs = c.fetch_gupy(client, {"company_id": company_id})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "11111"
    assert jobs[0]["title"] == "Comandante A320"
    assert jobs[0]["location"] == "Campinas, SP"
    assert jobs[0]["country_code"] == "BR"
    assert jobs[0]["employment_type"] == "full_time"
    assert jobs[0]["url"] == "https://voeazul.gupy.io/job/11111"


def test_workable_connector():
    """Workable connector fetches from public REST API."""
    company = "ryanair"
    page1 = {
        "jobs": [
            {
                "id": "001",
                "title": "Cabin Crew (F/M/X)",
                "url": "https://ryanair.workable.com/jobs/new/001",
                "location": {
                    "city": "Dublin",
                    "country": "Ireland",
                },
                "employment_type": "full_time",
            },
            {
                "id": "002",
                "title": "Ramp Agent",
                "url": "https://ryanair.workable.com/jobs/new/002",
                "location": {
                    "city": "Barcelona",
                    "country": "Spain",
                },
                "employment_type": "contract",
            },
        ]
    }
    client = FakeClient({"https://www.workable.com/api/v1/companies/ryanair/jobs": page1})
    jobs = c.fetch_workable(client, {"company": company})
    assert len(jobs) == 2
    assert jobs[0]["source_id"] == "001"
    assert jobs[0]["title"] == "Cabin Crew (F/M/X)"
    assert jobs[0]["location"] == "Dublin, Ireland"
    assert jobs[0]["country_code"] == "IE"
    assert jobs[0]["employment_type"] == "full_time"
    assert jobs[1]["employment_type"] == "contract"
    assert jobs[1]["country_code"] == "ES"


def test_hhru_connector():
    """hh.ru connector fetches vacancies from public REST API."""
    api_data = {
        "found": 2,
        "pages": 1,
        "per_page": 100,
        "page": 0,
        "items": [
            {
                "id": "101",
                "name": "Пилот / Pilot (Boeing 737)",
                "alternate_url": "https://hh.ru/vacancy/101",
                "area": {"id": "1", "name": "Москва"},
                "address": {"city": "Москва", "country": ""},
                "published_at": "2026-10-10T08:00:00+0300",
                "schedule": {"id": "fullDay", "name": "Полный день"},
                "employment": {"id": "full", "name": "Полная занятость"},
            },
            {
                "id": "202",
                "name": "Flight Attendant / Бортпроводник",
                "alternate_url": "https://hh.ru/vacancy/202",
                "area": {"id": "2", "name": "Санкт-Петербург"},
                "address": {},
                "published_at": "2026-10-09T10:00:00+0300",
                "schedule": {"id": "remote", "name": "Удалённая работа"},
                "employment": {"id": "part", "name": "Частичная занятость"},
            },
        ],
    }
    client = FakeClient({"https://api.hh.ru/vacancies": api_data})
    jobs = c.fetch_hhru(client, {"employer_id": "1455", "country": "RU"})
    assert len(jobs) == 2
    # First vacancy: Moscow, full-time, on-site
    assert jobs[0]["source_id"] == "101"
    assert jobs[0]["title"] == "Пилот / Pilot (Boeing 737)"
    assert jobs[0]["url"] == "https://hh.ru/vacancy/101"
    assert jobs[0]["location"] == "Москва"
    assert jobs[0]["country_code"] == "RU"
    assert jobs[0]["posted_date"] == "2026-10-10"
    assert jobs[0]["posted_estimated"] is False
    assert jobs[0]["employment_type"] == "full_time"
    assert jobs[0]["work_mode"] == "On-site"
    # Second vacancy: Saint Petersburg, part-time, remote
    assert jobs[1]["source_id"] == "202"
    assert jobs[1]["location"] == "Санкт-Петербург"
    assert jobs[1]["employment_type"] == "part_time"
    assert jobs[1]["work_mode"] == "Remote"


def test_airworks_connector():
    """Air Works' careers page had two separate bugs, both confirmed live on 20 Oct 2026.

    (1) fetch_airworks() called client.get(), a method that doesn't exist (the real client
    only has get_text(), get_json(), post_json()) - every run failed outright with
    "'PoliteClient' object has no attribute 'get'" (data/employer_status.json's last_error).
    Fixed by calling client.get_text().

    (2) Once that was fixed, the connector ran but returned zero jobs: _AirWorksParser was
    written around a <region> tag that never existed on the real page - confirmed by
    inspecting the live DOM, which has no such tag anywhere. The real markup is a Bootstrap
    div per job (div.row.border-bottom.pb-4), with two <small> tags (posted date, job ID),
    an <h4> title, a <ul> of location/type/department, and an <a> link. Rewrote the parser
    to match that real structure - this test's HTML is a direct copy of that structure.
    """
    html = """
    <html><body>
      <div class="container jobs-listing">
        <div class="row  py-4">
          <div class="col-lg-9">
            <div class="row border-bottom pb-4">
              <div class="col-lg-9">
                <small>Posted 03 May 2026</small>
                <small class="border-left pl-2 ml-2">Job ID: 22425</small>
                <h4 class="h4 m-0"><div class="badge"></div>Line Maintenance Engineer</h4>
                <div class="entry-meta"><ul class="mt-1">
                  <li class="no-separator">Mumbai, India</li>
                  <li>Full Time</li>
                  <li>Engineering & Maintenance</li>
                </ul></div>
                <a href="/careers/open-positions/line-maintenance-engineer">More Details</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body></html>
    """
    client = FakeClient({"https://airworks.aero/careers/open-positions": html})
    jobs = c.fetch_airworks(client, {"url": "https://airworks.aero/careers/open-positions"})
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Line Maintenance Engineer"
    assert jobs[0]["source_id"] == "22425"
    assert jobs[0]["url"] == "https://airworks.aero/careers/open-positions/line-maintenance-engineer"
    assert jobs[0]["location"] == "Mumbai, India"
    assert jobs[0]["employment_type"] == "Full Time"
    assert jobs[0]["department"] == "Engineering & Maintenance"
    assert jobs[0]["posted_date"] == "2026-05-03"


def test_airworks_connector_multiple_jobs_and_last_card_without_border():
    """The last job card on the real page has class "row  pb-4" (no border-bottom, since
    there's no following sibling to divide from) - make sure the div-depth tracking that
    finds each job block's real end tag doesn't get confused by that, or by two cards back
    to back."""
    def card(cls, title, job_id, location):
        return f"""
        <div class="{cls}">
          <div class="col-lg-9">
            <small>Posted 01 Jan 2026</small>
            <small class="border-left pl-2 ml-2">Job ID: {job_id}</small>
            <h4 class="h4 m-0"><div class="badge"></div>{title}</h4>
            <div class="entry-meta"><ul class="mt-1">
              <li class="no-separator">{location}</li>
              <li>Full Time</li>
              <li>Engineering</li>
            </ul></div>
            <a href="/careers/open-positions/{job_id}">More Details</a>
          </div>
        </div>
        """
    html = "<html><body><div class='container jobs-listing'>" + \
           card("row border-bottom pb-4", "First Job", "111", "Delhi") + \
           card("row  pb-4", "Second Job", "222", "Pune") + \
           "</div></body></html>"
    client = FakeClient({"https://airworks.aero/careers/open-positions": html})
    jobs = c.fetch_airworks(client, {"url": "https://airworks.aero/careers/open-positions"})
    assert len(jobs) == 2
    assert jobs[0]["title"] == "First Job" and jobs[0]["source_id"] == "111"
    assert jobs[1]["title"] == "Second Job" and jobs[1]["source_id"] == "222"
