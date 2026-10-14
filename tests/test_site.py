import json
import re

from fetcher.common import CONFIG_DIR, DATA_DIR
from site_builder.build import Builder, job_summary
from site_builder import sample


def test_build_with_sample_data(tmp_path):
    sample.main()
    out = tmp_path / "site"
    Builder(out, True, DATA_DIR / "sample" / "jobs.json", DATA_DIR / "sample" / "employers.yaml").build()
    index = json.loads((out / "data" / "jobs-index.json").read_text())
    assert len(index["jobs"]) > 50
    home = (out / "index.html").read_text()
    assert "Preview with sample data" in home and "noindex" in home
    job_pages = list((out / "jobs").glob("*/index.html"))
    assert len(job_pages) == len(index["jobs"])
    page = job_pages[0].read_text()
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    data = json.loads(m.group(1))
    assert data["@type"] == "JobPosting" and data["hiringOrganization"]["name"] and data["datePosted"]
    for path in ("about", "contact", "privacy", "terms", "guides", "companies", "countries", "roles/pilots"):
        assert (out / path / "index.html").exists(), path
    privacy = (out / "privacy" / "index.html").read_text()
    assert "Google" in privacy and "{{" not in privacy
    # every internal link in preview mode points at a file that exists
    for f in [out / "index.html", job_pages[0], out / "about" / "index.html"]:
        for href in re.findall(r'href="([^"#?]+)', f.read_text()):
            if href.startswith(("http", "mailto:")):
                continue
            assert (f.parent / href).resolve().exists(), (f, href)


def test_build_with_no_jobs(tmp_path):
    empty = tmp_path / "jobs.json"
    empty.write_text('{"jobs": {}}')
    out = tmp_path / "site"
    Builder(out, False, empty, CONFIG_DIR / "employers.yaml").build()
    assert "Jobs are on their way" in (out / "index.html").read_text()
    assert (out / "sitemap.xml").exists() and (out / "robots.txt").exists()


def test_summary_is_our_own_words():
    s = job_summary({"company": "Example Air", "title": "Ramp Agent", "role": "ground-operations",
                     "location": "Doha", "country": "Qatar", "work_mode": "On-site",
                     "employment_type": "Full-time", "posted_date": "2026-10-01", "posted_estimated": False})
    assert s.startswith("Example Air has a ground operations and airport services vacancy open: Ramp Agent.")
    assert "Doha, Qatar" in s and "an on-site, full-time position" in s


def test_security_headers_on_live_build(tmp_path):
    empty = tmp_path / "jobs.json"
    empty.write_text('{"jobs": {}}')
    out = tmp_path / "site"
    Builder(out, False, empty, CONFIG_DIR / "employers.yaml").build()
    headers = (out / "_headers").read_text()
    assert "frame-ancestors 'self'" in headers and "nosniff" in headers and "Strict-Transport-Security" in headers
