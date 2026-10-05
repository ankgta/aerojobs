"""Turn data/alerts.json into a GitHub issue, which GitHub emails to you.

Runs inside GitHub Actions after each fetch. If there is already an open alert
issue, it adds a comment instead of opening a new one.
"""
from __future__ import annotations

import subprocess
import sys

from .common import DATA_DIR, read_json

LABEL = "fetcher-alert"


def gh(*args: str, input_text: str | None = None) -> str:
    r = subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr.strip())
    return r.stdout.strip()


def main() -> int:
    data = read_json(DATA_DIR / "alerts.json", {"alerts": []})
    alerts = data.get("alerts") or []
    if not alerts:
        print("No alerts.")
        return 0
    lines = [f"Job fetcher run {data.get('run', '')}: {len(alerts)} employer(s) need a look.", ""]
    lines += [f"- **{a['employer']}**: {a['problem']}" for a in alerts]
    lines += ["", "Ask Claude to look at these. Other employers were updated normally."]
    body = "\n".join(lines)
    gh("label", "create", LABEL, "--color", "D93F0B", "--description", "Problems found by the job fetcher")
    existing = gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number", "--jq", ".[0].number")
    if existing:
        gh("issue", "comment", existing, "--body-file", "-", input_text=body)
    else:
        gh("issue", "create", "--title", "Job fetcher needs attention", "--label", LABEL,
           "--body-file", "-", input_text=body)
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
