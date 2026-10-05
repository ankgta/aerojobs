"""Quick health report on the job data.

    python qa/data_quality.py                 # uses data/jobs.json
    python qa/data_quality.py path/to/jobs.json

Prints, per employer: live jobs, share with a country, share whose role is unclear (default
"Corporate"), jobs still waiting for detail pages, coded locations, closing dates. Then totals,
role mix, and the last run's alerts. Read-only.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fetcher.run import is_visible  # noqa: E402


def pct(n, d):
    return f"{(100 * n / d):.0f}%" if d else "-"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "jobs.json"
    store = json.loads(path.read_text())
    jobs = [j for j in store["jobs"].values() if is_visible(j)]
    print(f"Data updated: {store.get('updated_at', '?')}   live jobs: {len(jobs)}   "
          f"stored (incl. hidden): {len(store['jobs'])}\n")
    by = collections.defaultdict(list)
    for j in jobs:
        by[j["company"]].append(j)
    head = f"{'Employer':42} {'Jobs':>5} {'Country':>8} {'Unclear':>8} {'Pending':>8} {'Coded':>6} {'Closing':>8}"
    print(head)
    print("-" * len(head))
    for name, lst in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n = len(lst)
        print(f"{name[:42]:42} {n:>5} {pct(sum(1 for j in lst if j.get('country_code')), n):>8} "
              f"{pct(sum(1 for j in lst if j.get('role_source') == 'default'), n):>8} "
              f"{sum(1 for j in lst if j.get('detail_pending')):>8} "
              f"{sum(1 for j in lst if '~' in (j.get('location') or '')):>6} "
              f"{sum(1 for j in lst if j.get('closing_date')):>8}")
    n = len(jobs)
    print("-" * len(head))
    print(f"{'TOTAL':42} {n:>5} {pct(sum(1 for j in jobs if j.get('country_code')), n):>8} "
          f"{pct(sum(1 for j in jobs if j.get('role_source') == 'default'), n):>8}")
    print(f"\nCountries: {len({j['country_code'] for j in jobs if j.get('country_code')})}")
    print("Roles:", dict(collections.Counter(j["role"] for j in jobs).most_common()))
    print("Work mode:", dict(collections.Counter(j["work_mode"] for j in jobs).most_common()))
    alerts = ROOT / "data" / "alerts.json"
    if alerts.exists():
        a = json.loads(alerts.read_text())
        print(f"\nLast run alerts ({a.get('run', '?')}):", a.get("alerts") or "none")


if __name__ == "__main__":
    main()
