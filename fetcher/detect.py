"""Find which hiring system a careers page uses, and suggest the config line.

    python -m fetcher.detect https://careers.example-airline.com
"""
from __future__ import annotations

import re
import sys
import urllib.parse

from .connectors import extract_job_postings
from .http import PoliteClient

PATTERNS = [
    ("workday", re.compile(r"https://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.(eu\.)?lever\.co/([A-Za-z0-9_.-]+)")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)")),
    ("successfactors", re.compile(r"(career\d*\.successfactors\.\w+|jobs\.sap\.com|\.jobs2web\.com)")),
    ("taleo", re.compile(r"([a-z0-9-]+\.taleo\.net)")),
    ("icims", re.compile(r"([a-z0-9-]+\.icims\.com)")),
    ("oracle", re.compile(r"([a-z0-9-]+\.fa\.[a-z0-9-]+\.oraclecloud\.com)(?:/hcmUI/CandidateExperience/[a-z]{2}/sites/([A-Za-z0-9_]+))?")),
]


def suggest(url: str, page: str) -> list[str]:
    found = []
    for name, pat in PATTERNS:
        m = pat.search(page) or pat.search(url)
        if not m:
            continue
        if name == "workday":
            found.append(f'source: {{ats: workday, url: "https://{m[1]}.{m[2]}.myworkdayjobs.com/{m[3]}"}}')
        elif name == "greenhouse":
            found.append(f'source: {{ats: greenhouse, board: "{m[1]}"}}')
        elif name == "lever":
            region = ", region: eu" if m[1] else ""
            found.append(f'source: {{ats: lever, company: "{m[2]}"{region}}}')
        elif name == "oracle":
            site = m[2] or "CX_1"
            found.append(f'source: {{ats: oracle, host: "{m[1]}", site: "{site}"}}' + ("" if m[2] else "   # site number guessed"))
        elif name == "smartrecruiters":
            found.append(f'source: {{ats: smartrecruiters, company: "{m[1]}"}}')
        else:
            found.append(f"# uses {name} ({m[1]}): no connector yet; try the jsonld reader or a custom reader")
    if extract_job_postings(page):
        found.append(f'source: {{ats: jsonld, listing_url: "{url}"}}   # page has Google JobPosting data')
    return found


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    client = PoliteClient()
    for url in argv:
        print(f"\n{url}")
        try:
            page = client.get_text(url)
        except Exception as e:
            print(f"  could not open: {e}")
            continue
        hits = suggest(url, page)
        if not hits:
            host = urllib.parse.urlsplit(url).netloc
            print(f"  no known hiring system found on {host}. The jobs may load later via script;"
                  " open the page in a browser and look where the 'Apply' links go.")
        for h in hits:
            print("  " + h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
