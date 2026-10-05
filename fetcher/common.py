"""Shared helpers: paths, config loading, slugs and dates."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"

COMPANY_TYPES = {
    "airline": "Airline",
    "airport": "Airport",
    "mro": "Maintenance (MRO)",
    "manufacturer": "Manufacturer",
    "ground_services": "Ground services",
    "other": "Other aviation",
}


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_site_config() -> dict:
    return load_yaml(CONFIG_DIR / "site.yaml")


def load_employers(path: Path | None = None) -> list[dict]:
    data = load_yaml(path or CONFIG_DIR / "employers.yaml")
    employers = data.get("employers") or []
    seen = set()
    for e in employers:
        if not e.get("slug"):
            e["slug"] = slugify(e["name"])
        if e["slug"] in seen:
            raise ValueError(f"Duplicate employer slug: {e['slug']}")
        seen.add(e["slug"])
        e.setdefault("type", "other")
        e.setdefault("enabled", False)
    return employers


def read_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def slugify(text: str, max_len: int = 70) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].rstrip("-") or "item"


def short_hash(text: str, n: int = 8) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_date(value) -> str | None:
    """Turn many date shapes into YYYY-MM-DD, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # epoch seconds or milliseconds
        secs = value / 1000 if value > 10_000_000_000 else value
        try:
            return dt.datetime.fromtimestamp(secs, dt.timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return dt.date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%B %d, %Y", "%d %B %Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def safe_url(url) -> str | None:
    """Only ordinary web links (https:// or http://) are allowed as Apply links.
    Anything else, such as javascript: or data: links, is rejected."""
    if not isinstance(url, str):
        return None
    u = url.strip()
    if re.match(r"^https?://[^\s/?#]+\.[^\s/?#]+", u, re.I) and not re.search(r"[\s<>\"']", u):
        return u
    return None
