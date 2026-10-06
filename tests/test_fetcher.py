import datetime as dt

from fetcher import connectors as c
from fetcher.geo import country_from_location, region_of
from fetcher.roles import classify_title, detect_work_mode, is_aviation_job
from fetcher.run import merge_employer_jobs, purge_expired, is_visible


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

    def get_json(self, url, **kw):
        return self._get(url)

    def get_text(self, url):
        return self._get(url)

    def post_json(self, url, payload):
        self.calls.append((url, payload["offset"]))
        return self.responses[url][payload["offset"] // 20]


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
