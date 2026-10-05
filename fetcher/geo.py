"""Countries, regions, and reading a country out of a free-text location."""
from __future__ import annotations

import re
from functools import lru_cache

import pycountry

REGIONS = {
    "Middle East": "AE BH IQ IR IL JO KW LB OM PS QA SA SY YE",
    "Europe": ("AD AL AM AT AZ BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GE GG GI GR HR HU IE IM "
               "IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM TR UA VA XK"),
    "North America": "US CA BM GL PM",
    "Latin America and Caribbean": (
        "MX GT BZ SV HN NI CR PA CU DO HT JM PR BS BB TT AG DM GD KN LC VC AW CW SX KY TC VG VI "
        "AI MS BQ MF BL GP MQ CO VE EC PE BO BR PY UY AR CL GY SR GF FK"),
    "Asia": ("AF BD BT BN KH CN HK MO IN ID JP KZ KG LA MY MV MN MM NP KP KR PK PH SG LK TW TJ TH "
             "TL TM UZ VN"),
    "Oceania": "AU NZ FJ PG SB VU NC PF WS TO KI FM MH NR PW TV GU MP AS CK NU",
    "Africa": ("DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS "
               "LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW SH ST SN SC SL SO ZA SS SD TZ TG TN "
               "UG EH ZM ZW"),
}
REGION_ORDER = list(REGIONS)
_REGION_OF = {code: region for region, codes in REGIONS.items() for code in codes.split()}

DISPLAY_NAMES = {
    "GB": "United Kingdom", "US": "United States", "KR": "South Korea", "KP": "North Korea",
    "RU": "Russia", "VN": "Vietnam", "IR": "Iran", "TR": "Türkiye", "HK": "Hong Kong",
    "MO": "Macao", "TW": "Taiwan", "TZ": "Tanzania", "VE": "Venezuela", "BO": "Bolivia",
    "SY": "Syria", "LA": "Laos", "MD": "Moldova", "PS": "Palestine", "CZ": "Czechia",
    "CD": "DR Congo", "CG": "Congo", "BN": "Brunei", "XK": "Kosovo", "CI": "Côte d'Ivoire",
}

ALIASES = {
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB", "england": "GB",
    "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "usa": "US", "u.s.": "US", "u.s.a.": "US", "united states of america": "US", "america": "US",
    "uae": "AE", "u.a.e.": "AE", "ksa": "SA", "kingdom of saudi arabia": "SA",
    "russia": "RU", "south korea": "KR", "korea": "KR", "republic of korea": "KR",
    "vietnam": "VN", "turkey": "TR", "türkiye": "TR", "turkiye": "TR", "czech republic": "CZ",
    "holland": "NL", "the netherlands": "NL", "hong kong sar": "HK", "taiwan": "TW", "iran": "IR",
    "laos": "LA", "bolivia": "BO", "venezuela": "VE", "tanzania": "TZ", "macau": "MO",
    "ivory coast": "CI", "cote d'ivoire": "CI", "kosovo": "XK", "brunei": "BN", "syria": "SY",
    "moldova": "MD", "palestine": "PS", "dr congo": "CD", "drc": "CD",
}

# A few big aviation hubs that are often written without a country.
CITIES = {
    "dubai": "AE", "abu dhabi": "AE", "sharjah": "AE", "doha": "QA", "riyadh": "SA",
    "jeddah": "SA", "dammam": "SA", "muscat": "OM", "manama": "BH", "kuwait city": "KW",
    "london": "GB", "heathrow": "GB", "gatwick": "GB", "manchester": "GB", "paris": "FR",
    "toulouse": "FR", "hamburg": "DE", "frankfurt": "DE", "munich": "DE", "amsterdam": "NL",
    "dublin": "IE", "istanbul": "TR", "madrid": "ES", "zurich": "CH", "mumbai": "IN",
    "delhi": "IN", "new delhi": "IN", "gurgaon": "IN", "gurugram": "IN", "bengaluru": "IN",
    "bangalore": "IN", "hyderabad": "IN", "chennai": "IN", "sydney": "AU", "melbourne": "AU",
    "brisbane": "AU", "auckland": "NZ", "tokyo": "JP", "seoul": "KR", "bangkok": "TH",
    "kuala lumpur": "MY", "jakarta": "ID", "manila": "PH", "addis ababa": "ET",
    "nairobi": "KE", "johannesburg": "ZA", "cape town": "ZA", "cairo": "EG",
    "toronto": "CA", "montreal": "CA", "vancouver": "CA", "calgary": "CA",
    "sao paulo": "BR", "são paulo": "BR", "mexico city": "MX", "bogota": "CO", "bogotá": "CO",
    "santiago": "CL", "panama city": "PA", "lima": "PE",
}

US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
                "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
CA_PROVINCES = set("AB BC MB NB NL NS NT NU ON PE QC SK YT".split())


@lru_cache(maxsize=1)
def _name_index() -> dict[str, str]:
    idx = {}
    for c in pycountry.countries:
        for attr in ("name", "common_name", "official_name"):
            v = getattr(c, attr, None)
            if v:
                idx[v.lower()] = c.alpha_2
    idx.update(ALIASES)
    return idx


@lru_cache(maxsize=1)
def _alpha3_index() -> dict[str, str]:
    return {c.alpha_3: c.alpha_2 for c in pycountry.countries}


def is_country_code(code: str | None) -> bool:
    return bool(code) and (code.upper() in _REGION_OF or pycountry.countries.get(alpha_2=code.upper()) is not None)


def country_name(code: str | None) -> str | None:
    if not code:
        return None
    code = code.upper()
    if code in DISPLAY_NAMES:
        return DISPLAY_NAMES[code]
    c = pycountry.countries.get(alpha_2=code)
    if not c:
        return None
    return getattr(c, "common_name", None) or c.name


def region_of(code: str | None) -> str:
    return _REGION_OF.get((code or "").upper(), "Other")


def lookup_country(text: str | None) -> str | None:
    """Return a two-letter country code for a country name/code, or None."""
    if not text:
        return None
    t = text.strip().strip(".").strip()
    if not t:
        return None
    key = t.lower()
    if key in _name_index():
        return _name_index()[key]
    if len(t) == 3 and t.isupper() and t in _alpha3_index():
        return _alpha3_index()[t]
    if len(t) == 2 and t.isalpha() and t.upper() in _REGION_OF:
        return t.upper()
    return None


def country_from_location(location: str | None) -> str | None:
    """Best-effort: read a country code from text like 'Seattle, WA' or 'Dubai - UAE'."""
    if not location:
        return None
    whole = lookup_country(location)
    if whole:
        return whole
    tokens = [t.strip() for t in re.split(r"[,|/;()\n]| - | – ", location) if t.strip()]
    # 1) full country names, last token first
    for tok in reversed(tokens):
        if len(tok) > 3:
            code = lookup_country(tok)
            if code:
                return code
    # 2) known hub cities
    for tok in reversed(tokens):
        code = CITIES.get(tok.lower())
        if code:
            return code
    upper_tokens = [t for t in tokens if t.isupper() and t.isalpha()]
    # 3) Canadian provinces, then US states (so "San Jose, CA" means California)
    if any(t in CA_PROVINCES for t in upper_tokens):
        return "CA"
    if len(tokens) >= 2 and any(t in US_STATES for t in upper_tokens):
        return "US"
    # 4) three- and two-letter country codes
    for tok in reversed(upper_tokens):
        code = lookup_country(tok)
        if code:
            return code
    return None
