"""Make made-up sample data for previewing the website:  python -m site_builder.sample

Every employer and job here is fictional. The preview build shows a banner saying so.
"""
from __future__ import annotations

import datetime as dt
import random

import yaml

from fetcher.common import DATA_DIR, now_iso, today, write_json
from fetcher.run import merge_employer_jobs

EMPLOYERS = [
    {"name": "Harbourline Air", "slug": "harbourline-air", "type": "airline", "country": "GB",
     "places": ["London Heathrow, United Kingdom", "Manchester, United Kingdom", "Glasgow, United Kingdom"]},
    {"name": "Dune Coast Airlines", "slug": "dune-coast-airlines", "type": "airline", "country": "AE",
     "places": ["Dubai, United Arab Emirates", "Abu Dhabi, United Arab Emirates", "Mumbai, India"]},
    {"name": "Kestrel Regional", "slug": "kestrel-regional", "type": "airline", "country": "US",
     "places": ["Denver, CO", "Seattle, WA", "Phoenix, AZ"]},
    {"name": "Larkspur Airways", "slug": "larkspur-airways", "type": "airline", "country": "IN",
     "places": ["Gurugram, India", "Bengaluru, India", "Hyderabad, India"]},
    {"name": "Tasman Arc Airlines", "slug": "tasman-arc-airlines", "type": "airline", "country": "NZ",
     "places": ["Auckland, New Zealand", "Sydney, Australia"]},
    {"name": "Brightfield Airport", "slug": "brightfield-airport", "type": "airport", "country": "GB",
     "places": ["Brightfield Airport, United Kingdom"]},
    {"name": "Corvid Aero Services", "slug": "corvid-aero-services", "type": "mro", "country": "SG",
     "places": ["Singapore", "Kuala Lumpur, Malaysia", "Hamburg, Germany"]},
    {"name": "Orrery Aerospace", "slug": "orrery-aerospace", "type": "manufacturer", "country": "FR",
     "places": ["Toulouse, France", "Hamburg, Germany", "Montreal, QC", "Remote - France"]},
    {"name": "Ridgeline Ground Handling", "slug": "ridgeline-ground-handling", "type": "ground_services",
     "country": "QA", "places": ["Doha, Qatar", "Riyadh, Saudi Arabia", "Nairobi, Kenya"]},
]

TITLES = {
    "airline": ["First Officer A320", "Captain - Boeing 787", "Cadet Pilot Programme 2027", "Cabin Crew",
                "Senior Flight Attendant", "Flight Dispatcher", "Crew Scheduling Officer",
                "Customer Service Agent", "Revenue Management Analyst (Hybrid)", "Cargo Sales Executive",
                "Software Engineer, Mobile App", "HR Business Partner", "B1 Licensed Aircraft Engineer"],
    "airport": ["Airside Operations Officer", "Security Officer", "Baggage Systems Technician",
                "Terminal Duty Manager", "Customer Experience Ambassador", "Finance Business Partner (Hybrid)"],
    "mro": ["B2 Avionics Engineer", "Aircraft Maintenance Technician", "NDT Inspector Level 2",
            "Composite Repair Technician", "Maintenance Planner", "Quality Auditor"],
    "manufacturer": ["Stress Engineer", "Systems Engineer - Flight Controls", "Flight Test Engineer",
                     "Manufacturing Engineer", "Supply Chain Analyst", "Data Scientist (Remote)",
                     "Procurement Specialist"],
    "ground_services": ["Ramp Agent", "Passenger Services Agent", "Load Control Officer",
                        "Cargo Warehouse Supervisor", "Station Manager", "Aircraft Refueller"],
}


def main() -> None:
    rnd = random.Random(42)
    run_date = today()
    jobs: dict = {}
    for emp in EMPLOYERS:
        raws = []
        for n, title in enumerate(TITLES[emp["type"]]):
            for k in range(rnd.choice([1, 1, 2])):
                age = rnd.choice([0, 0, 1, 1, 2, 3, 5, 6, 9, 12, 16, 21, 27, 35, 44, 52])
                closing = run_date + dt.timedelta(days=rnd.choice([4, 9, 14, 21, 30])) if rnd.random() < .35 else None
                raws.append({
                    "source_id": f"{emp['slug']}-{n}-{k}",
                    "title": title,
                    "url": "https://example.com/careers",
                    "location": rnd.choice(emp["places"]),
                    "posted_date": (run_date - dt.timedelta(days=age)).isoformat(),
                    "posted_estimated": rnd.random() < .2,
                    "closing_date": closing.isoformat() if closing else None,
                    "employment_type": rnd.choice(["Full time", "Full time", "Full time", "Contract", "Part time"]),
                })
        merge_employer_jobs(jobs, emp, raws, run_date.isoformat())
    for j in jobs.values():
        if not j.get("role"):
            j["role"], j["role_source"] = "corporate", "default"
    out = DATA_DIR / "sample"
    write_json(out / "jobs.json", {"updated_at": now_iso(), "jobs": jobs})
    emps = [{k: v for k, v in e.items() if k != "places"} | {"enabled": True} for e in EMPLOYERS]
    (out / "employers.yaml").write_text(yaml.safe_dump({"employers": emps}, sort_keys=False, allow_unicode=True))
    print(f"Wrote {len(jobs)} sample jobs to {out}")


if __name__ == "__main__":
    main()
