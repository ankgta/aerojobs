"""Find aviation organisations from the .aero directory at information.aero.

    python -m fetcher.discover_aero              # list every .aero website in the directory
    python -m fetcher.discover_aero --check 200  # also look for a careers page on up to 200 of them

Step 1 reads the directory's public listing pages (allowed by its robots.txt; its search
pages are not, so they are never used) and saves data/aero_directory.csv.
Step 2 visits each organisation's home page, looks for a careers / jobs link, and works out
which hiring system that page uses. Results go to data/aero_candidates.csv.

Nothing is switched on automatically: candidates are reviewed, then added to
config/employers.yaml by hand. Only names and web addresses are stored, never the
directory's descriptions.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.parse
from html.parser import HTMLParser

from .common import DATA_DIR, today
from .detect import suggest
from .http import PoliteClient

LISTING_URL = "https://information.aero/taxonomy/term/all?page={page}"
DIRECTORY_FILE = DATA_DIR / "aero_directory.csv"
CANDIDATES_FILE = DATA_DIR / "aero_candidates.csv"
CAREERS_WORDS = re.compile(r"career|jobs?\b|vacanc|recruit|join[\s-]?(us|our)|work[\s-]?with[\s-]?us|employment|hiring", re.I)


class _Anchors(HTMLParser):
    """Collects (href, visible text) for every link on a page."""
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def anchors(html: str) -> list[tuple[str, str]]:
    p = _Anchors()
    p.feed(html)
    return p.links


def aero_sites_on_page(html: str) -> list[dict]:
    """External .aero websites linked from a directory listing page."""
    found, seen = [], set()
    for href, text in anchors(html):
        parts = urllib.parse.urlsplit(href)
        host = (parts.hostname or "").lower()
        if parts.scheme not in ("http", "https") or not host.endswith(".aero"):
            continue
        if host.endswith("information.aero"):
            continue
        domain = host[4:] if host.startswith("www.") else host
        if domain in seen:
            continue
        seen.add(domain)
        name = text if text and not text.lower().startswith(("http", "www.")) else ""
        found.append({"name": name, "domain": domain, "url": f"https://{host}/"})
    return found


def careers_link(home_url: str, html: str) -> str | None:
    """Best guess at the careers page linked from an organisation's home page."""
    best = None
    for href, text in anchors(html):
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        if CAREERS_WORDS.search(text) or CAREERS_WORDS.search(href):
            url = urllib.parse.urljoin(home_url, href.split("#")[0])
            if CAREERS_WORDS.search(text) and CAREERS_WORDS.search(href):
                return url
            best = best or url
    return best


def read_directory(client: PoliteClient, max_pages: int = 400) -> list[dict]:
    sites: dict[str, dict] = {}
    for page in range(max_pages):
        try:
            html = client.get_text(LISTING_URL.format(page=page))
        except Exception as e:  # stop at the first page that fails or does not exist
            print(f"  stopped at page {page}: {e}")
            break
        new = [s for s in aero_sites_on_page(html) if s["domain"] not in sites]
        if not new:
            print(f"  page {page}: no new websites, finished")
            break
        for s in new:
            sites[s["domain"]] = s
        print(f"  page {page}: {len(new)} new, {len(sites)} total", flush=True)
    return sorted(sites.values(), key=lambda s: s["domain"])


def check_sites(client: PoliteClient, sites: list[dict], limit: int) -> list[dict]:
    rows = []
    for s in sites[:limit]:
        row = {"name": s["name"], "domain": s["domain"], "website": s["url"],
               "careers_url": "", "hiring_system": "", "suggested_source": "", "note": ""}
        try:
            home = client.get_text(s["url"])
            link = careers_link(s["url"], home)
            if not link:
                row["note"] = "no careers link found on home page"
            else:
                row["careers_url"] = link
                hits = suggest(link, client.get_text(link))
                usable = [h for h in hits if h.startswith("source:")]
                row["suggested_source"] = usable[0] if usable else ""
                row["hiring_system"] = (re.search(r"ats: (\w+)", usable[0]).group(1) if usable
                                        else (hits[0].split("(")[0].replace("# uses", "").strip() if hits else "unknown"))
                if not usable:
                    row["note"] = "careers page found; needs a custom reader or manual check"
        except Exception as e:
            row["note"] = f"could not open: {str(e)[:80]}"
        print(f"  {s['domain']}: {row['hiring_system'] or row['note']}", flush=True)
        rows.append(row)
    return rows


def write_csv(path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", type=int, default=0, metavar="N",
                    help="look for careers pages on up to N of the websites found")
    ap.add_argument("--max-pages", type=int, default=400)
    args = ap.parse_args(argv)
    client = PoliteClient(delay=2.0)

    print("Reading the .aero directory at information.aero ...")
    sites = read_directory(client, args.max_pages)
    for s in sites:
        s["first_seen"] = today().isoformat()
    write_csv(DIRECTORY_FILE, sites, ["name", "domain", "url", "first_seen"])
    print(f"Saved {len(sites)} websites to {DIRECTORY_FILE.name}")

    if args.check:
        print(f"\nLooking for careers pages on up to {args.check} websites ...")
        rows = check_sites(client, sites, args.check)
        write_csv(CANDIDATES_FILE, rows, ["name", "domain", "website", "careers_url",
                                          "hiring_system", "suggested_source", "note"])
        ready = sum(1 for r in rows if r["suggested_source"])
        print(f"Saved {len(rows)} results to {CANDIDATES_FILE.name}: {ready} ready to switch on after review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
