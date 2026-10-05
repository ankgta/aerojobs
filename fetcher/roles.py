"""Sort job titles into role categories, and detect remote / hybrid / on-site."""
from __future__ import annotations

import re

ROLES = {
    "pilots": "Pilots",
    "cabin-crew": "Cabin crew",
    "engineering-maintenance": "Aircraft engineering and maintenance (MRO)",
    "ground-operations": "Ground operations and airport services",
    "flight-operations": "Air traffic and flight operations",
    "cargo-logistics": "Cargo and logistics",
    "customer-service-sales": "Customer service and sales",
    "corporate": "Corporate (IT, finance, HR, other)",
}
DEFAULT_ROLE = "corporate"
ROLE_SHORT = {
    "pilots": "Pilots", "cabin-crew": "Cabin crew", "engineering-maintenance": "Engineering and MRO",
    "ground-operations": "Ground operations", "flight-operations": "ATC and flight ops",
    "cargo-logistics": "Cargo", "customer-service-sales": "Customer service", "corporate": "Corporate",
}

# Checked top to bottom; the first match wins, so more specific groups come first.
# Each pattern only matches whole words ("ramp" does not match "trampoline").
_RULES: list[tuple[str, list[str]]] = [
    ("cabin-crew", [r"cabin crew", r"flight attendants?", r"cabin attendants?", r"cabin manager",
                    r"pursers?", r"stewards?", r"stewardess"]),
    ("pilots", [r"pilots?", r"first officers?", r"second officers?", r"captains?", r"co-?pilots?",
                r"flight instructors?", r"type rating instructor", r"\btri\b", r"\btre\b", r"cadets?",
                r"flight crew"]),
    ("flight-operations", [r"air traffic", r"\batc\b", r"\batco\b", r"flight dispatch\w*", r"dispatchers?",
                           r"operations control", r"\bocc\b", r"crew control", r"crew scheduling",
                           r"crew planning", r"load control", r"load ?masters?", r"flight planning",
                           r"flight operations", r"flight ops", r"navigation", r"aeronautical information"]),
    # Clear IT / office titles, checked before maintenance words like "technician".
    ("corporate", [r"software", r"developer", r"\w*(?:entwickler|developpeur|développeur|informatik)\w*", r"it support", r"it technician", r"service desk",
                   r"help ?desk", r"cyber ?security", r"data (scientist|engineer|analyst)",
                   r"network engineer", r"cloud engineer", r"devops", r"facilities maintenance"]),
    ("engineering-maintenance", [r"\w*(?:techniker|tekniker|mechaniker|mecanicien|mécanicien|technicien|ingenieur|ingénieur|ingeniero|tecnico|técnico|monteur|elektroniker|fluggerat|fluggerät|kennzeichner)\w*",
                                 r"machinists?", r"cnc", r"assembl(?:er|y)", r"fabricat\w+", r"welders?",
                                 r"production (?:operator|technician|associate|supervisor|team leader)",
                                 r"manufacturing", r"tool ?setters?", r"material handlers?",
                                 r"computerized machine operator", r"\bcmo\b",
                                 r"quality (?:inspector|technician|engineer)", r"test (?:technician|engineer)",
                                 r"aircraft maintenance", r"\bame\b", r"\bb1\b", r"\bb2\b", r"\ba&p\b",
                                 r"mechanics?", r"technicians?", r"avionics", r"\bmro\b", r"maintenance",
                                 r"airframe", r"powerplant", r"\bndt\b", r"inspectors?", r"line station",
                                 r"hangar", r"engine shop", r"engine lines?", r"overhaul", r"repair", r"composite",
                                 r"airworthiness", r"structures? engineer", r"stress engineer",
                                 r"aerospace engineer", r"aeronautical engineer", r"aircraft engineer",
                                 r"licen[cs]ed engineer", r"certifying",
                                 r"superviseur\w*\s*-?\s*(?:ligne|production|moteur)", r"ligne de moteur",
                                 r"environmental health and safety", r"\behs\b",
                                 r"industrial engineer\w*"]),
    ("cargo-logistics", [r"cargo", r"freight", r"logistics", r"warehouse", r"supply chain", r"ulds?",
                         r"forwarding", r"shipping"]),
    ("ground-operations", [r"ground (handling|operations|services|staff|crew)", r"ramp", r"baggage",
                           r"check-?in", r"airport operations", r"aircraft handl\w+", r"fuell?ers?",
                           r"refuel\w*", r"de-?icing", r"passenger services?", r"terminal",
                           r"turnaround", r"aviation security", r"security (officer|screener)",
                           r"apron", r"airside", r"marshall\w*", r"\bgse\b", r"porters?",
                           r"wheelchair", r"station (manager|agent)", r"duty manager"]),
    ("customer-service-sales", [r"customer service", r"customer care", r"contact cent(er|re)",
                                r"call cent(er|re)", r"sales", r"reservations?", r"ticketing",
                                r"lounge", r"guest", r"customer experience", r"account manager",
                                r"business development", r"travel consultant"]),
    ("corporate", [r"software", r"developer", r"\bdata\b", r"cyber", r"\bit\b", r"network",
                   r"cloud", r"finance", r"financial", r"accountant", r"accounting", r"audit",
                   r"\bhr\b", r"human resources", r"recruit\w*", r"talent", r"payroll", r"legal",
                   r"counsel", r"lawyer", r"marketing", r"communications", r"procurement",
                   r"buyer", r"analyst", r"administrat\w+", r"assistant", r"secretary", r"intern",
                   r"product manager", r"project manager", r"program manager", r"program lead",
                   r"program specialist", r"scrum master", r"functional manager", r"designer",
                   r"engineer"]),  # generic "engineer" left over after aviation rules -> corporate tech
]
_COMPILED = [(role, [re.compile(r"\b(?:" + p + r")\b", re.I) for p in pats]) for role, pats in _RULES]

# Manufacturers' generic engineering jobs (design, systems, test) belong with aircraft engineering.
_MANUFACTURER_ENGINEERING = re.compile(
    r"\b(mechanical|systems?|design|test|flight test|propulsion|manufacturing|quality|production|"
    r"electrical|structural|materials|certification|reliability)\b.*\bengineer", re.I)


def classify_title(title: str, company_type: str | None = None) -> str | None:
    """Return a role key, or None when the title is unclear."""
    if not title:
        return None
    for role, patterns in _COMPILED:
        if role == "corporate" and company_type in ("manufacturer", "mro") and _MANUFACTURER_ENGINEERING.search(title):
            return "engineering-maintenance"
        if any(p.search(title) for p in patterns):
            return role
    return None


_REMOTE = re.compile(r"\b(remote|work from home|wfh|telecommute|home-?based|anywhere)\b", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)


def detect_work_mode(*texts: str | None, structured: str | None = None) -> str:
    """Return 'Remote', 'Hybrid' or 'On-site'. Aviation roles are on-site unless a source says otherwise."""
    s = (structured or "").strip().lower().replace("_", "-")
    if s in ("remote", "fully remote", "telecommute"):
        return "Remote"
    if s in ("hybrid", "flexible"):
        return "Hybrid"
    if s in ("on-site", "onsite", "on site", "office", "in-office"):
        return "On-site"
    blob = " ".join(t for t in texts if t)
    if _HYBRID.search(blob):
        return "Hybrid"
    if _REMOTE.search(blob):
        return "Remote"
    return "On-site"


def normalize_employment_type(value: str | None) -> str | None:
    if not value:
        return None
    v = value.lower()
    if "part" in v:
        return "Part-time"
    if "intern" in v:
        return "Internship"
    if "temp" in v or "contract" in v or "fixed" in v:
        return "Contract"
    if "full" in v or "permanent" in v or "regular" in v:
        return "Full-time"
    return None
