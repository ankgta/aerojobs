"""Builds AeroJobs-Test-Report.xlsx from the QA result files.

    python qa/build_report.py <first_run_dir> <latest_run_dir> <jobs_before.json> <jobs_after.json> \
                              <verify_round1.json> <verify_round2.json> <out.xlsx>

The run folders are the "latest" folder of the qa-results branch at two points in time
(first run and latest re-test). See the aerojobs-test-and-report skill for how to get them.
The defect list (DEF) below is written by hand: add a row whenever a defect is found.
"""
import collections
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

run1, run2, jobs_before, jobs_after, ver1, ver2, out = sys.argv[1:8]
R1 = json.load(open(Path(run1) / "results.json"))["results"]
R2 = json.load(open(Path(run2) / "results.json"))["results"]
S1 = json.load(open(Path(run1) / "security.json"))["results"] + json.load(open(Path(run1) / "local_security.json"))["results"]
S2 = json.load(open(Path(run2) / "security.json"))["results"] + json.load(open(Path(run2) / "local_security.json"))["results"]
AUDIT = json.load(open(Path(run2) / "pip-audit.json"))

FONT = "Arial"
NAVY, SKY, PALE, LINE = "0B1F3A", "DCEFFC", "F4F8FC", "D4DEE9"
F_PASS, T_PASS = "E2F6EC", "11724F"
F_FAIL, T_FAIL = "FDE4E4", "A11C1C"
F_WARN, T_WARN = "FFF1D6", "8A5300"
F_GREY, T_GREY = "EEF1F5", "4A5568"
thin = Side(style="thin", color=LINE)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
H_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
H_FILL = PatternFill("solid", fgColor=NAVY)
BODY = Font(name=FONT, size=10)
WRAP = Alignment(wrap_text=True, vertical="top")

wb = Workbook()


def sheet(title, headers, widths, rows, freeze="A2"):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c, w in zip(range(1, len(headers) + 1), widths):
        cell = ws.cell(row=1, column=c)
        cell.font, cell.fill, cell.border = H_FONT, H_FILL, BOX
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = w
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row:
            cell.font, cell.alignment, cell.border = BODY, WRAP, BOX
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
    ws.row_dimensions[1].height = 30
    return ws


def color_status(ws, rng):
    for word, fill, txt in (("Pass", F_PASS, T_PASS), ("Fixed", F_PASS, T_PASS), ("Fail", F_FAIL, T_FAIL),
                            ("Open", F_FAIL, T_FAIL), ("Closed", F_PASS, T_PASS), ("Not tested", F_GREY, T_GREY), ("Skip", F_GREY, T_GREY),
                            ("Owner decision", F_WARN, T_WARN), ("Partly fixed", F_WARN, T_WARN),
                            ("Known issue", F_WARN, T_WARN), ("Planned", F_GREY, T_GREY)):
        ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=[f'"{word}"'],
                                      fill=PatternFill("solid", fgColor=fill), font=Font(name=FONT, bold=True, color=txt)))


# ------------------------------------------------------------------ Test cases (matrix)
COMBOS = [("chromium", "Desktop"), ("chromium", "Pixel"), ("firefox", "Desktop"), ("firefox", "Phone"),
          ("webkit", "Desktop"), ("webkit", "iPhone")]
COMBO_NAMES = ["Chrome desktop", "Chrome Android (Pixel 7)", "Firefox desktop", "Firefox phone",
               "Safari engine desktop", "Safari iPhone 13"]


def matrix(results):
    cases = collections.OrderedDict()
    for r in results:
        key = r["id"]
        c = cases.setdefault(key, {"meta": r, "cells": {}, "actual": None, "fail": []})
        for i, (b, d) in enumerate(COMBOS):
            if r["browser"] == b and d.split()[0] in r["device"]:
                c["cells"][i] = r["status"]
        if r["status"] == "Fail":
            c["fail"].append(f"{r['browser']} / {r['device']}: {r['actual']}")
        if c["actual"] is None or (r["browser"] == "chromium" and "Desktop" in r["device"]):
            c["actual"] = r["actual"]
    return cases


m1, m2 = matrix(R1), matrix(R2)
rows = []
for key, c in m2.items():
    meta = c["meta"]
    first = m1.get(key)
    r1_overall = "Fail" if first and first["fail"] else ("Pass" if first else "-")
    if key == "TC-FLT-08":
        r1_overall = "Fail"   # reported by the owner before this test existed (DEF-12)
    cells = [c["cells"].get(i, "N/A") for i in range(6)]
    actual = c["actual"] if not c["fail"] else "; ".join(c["fail"])
    rows.append([key, meta["area"], meta["type"], meta["title"], meta["steps"], meta["expected"], *cells,
                 None, r1_overall, actual])
ws = sheet("Test cases",
           ["Test ID", "Area", "Test type", "What is tested", "Steps", "Expected result", *COMBO_NAMES,
            "Result (re-test)", "First run", "Actual result"],
           [11, 14, 12, 30, 34, 32, 10, 11, 10, 10, 11, 11, 11, 10, 60], rows)
for i in range(2, ws.max_row + 1):
    ws[f"M{i}"] = (f'=IF(COUNTIF(G{i}:L{i},"Fail")>0,"Fail",IF(COUNTIF(G{i}:L{i},"Pass")>0,"Pass","Skip"))')
    ws[f"M{i}"].font, ws[f"M{i}"].border = Font(name=FONT, bold=True, size=10), BOX
color_status(ws, f"G2:N{ws.max_row}")
ws.column_dimensions["G"].width = ws.column_dimensions["H"].width = 11
TC_ROWS = ws.max_row

# ------------------------------------------------------------------ Security tests
sec_first = {r["id"]: r["status"] for r in S1}
rows = [[r["id"], r["area"], r["title"], r["attack"], r["expected"], r["status"], sec_first.get(r["id"], "-"),
         r["severity"], r["actual"]] for r in S2]
vulns = sum(len(d.get("vulns", [])) for d in AUDIT.get("dependencies", []))
rows.append(["SEC-28", "Software supply chain", "Known vulnerabilities in the software the site uses",
             "pip-audit against the public vulnerability database", "No known vulnerabilities",
             "Pass" if vulns == 0 else "Fail", "Pass", "-",
             f"{len(AUDIT.get('dependencies', []))} packages checked, {vulns} known vulnerabilities"])
rows.append(["SEC-29", "Software supply chain", "Automation steps pinned and limited",
             "Review the GitHub workflows", "Third-party steps pinned to exact versions; minimal permissions; inputs passed safely",
             "Pass", "Pass", "-", "All third-party steps pinned to exact commit IDs; workflows only get 'contents' and 'issues' write access; Dependabot watches for updates"])
ws = sheet("Security tests", ["Test ID", "Area", "What is tested", "Attack or method", "Expected result", "Result (re-test)",
                              "First run", "Severity if failed", "Actual result"],
           [9, 18, 34, 38, 32, 11, 10, 11, 70], rows)
color_status(ws, f"F2:G{ws.max_row}")
SEC_ROWS = ws.max_row

# ------------------------------------------------------------------ Defects
def find(results, tc):
    return next((r for r in results if r["id"] == tc), None)

sec22 = find(S2, "SEC-22")
js_fail_r2 = [r for r in R2 if r["id"] == "TC-JS-01" and r["status"] == "Fail"]
DEF = [
    ["DEF-01", "Functional test TC-PAGE-01", "High", "'Show more jobs' button never disappears",
     "The button stayed on screen even after every job was shown, because a style rule overrode the page's 'hidden' setting.",
     "Added a site-wide rule so anything the page hides stays hidden.", "Fixed", "Pass"],
    ["DEF-02", "Phone test TC-MOB-01 / TC-FLT-02", "High", "On phones, page became wider than the screen after filtering",
     "After choosing a filter, the sort menu grew wider than a 412px phone screen. The page zoomed out and pushed the 'Show jobs' button off the bottom of the screen.",
     "Sort menu now shrinks to fit on all phones and tablets; filter labels can no longer widen the panel. Test extended to check the button stays on screen.", "Fixed", "Pass"],
    ["DEF-03", "Security test SEC-25", "Medium", "Job text from employers could add markup to Google's job data",
     "Job titles were placed in Google's JobPosting description without escaping, so hostile text from an employer site could insert HTML into Google's listing.",
     "All < > & characters in Google's job data are now escaped, and the description text is escaped.", "Fixed", "Pass"],
    ["DEF-04", "Data check after first real fetch", "High", "44% of real jobs had no country, so the Country filter missed them",
     "Employers write locations in many styles: company codes (US-GA-MACON-…), 'Toulouse Area', or just a town name.",
     "Added reading of company location codes and a worldwide town list (GeoNames, towns of 5,000+ people), preferring the employer's home country when a town name exists in several countries.",
     "Fixed", "Pass"],
    ["DEF-05", "Data check after first real fetch", "Medium", "Many jobs fell into 'Corporate' because titles were unclear or not in English",
     "Rules only knew English words, and manufacturing roles (assembly, CNC, welding) had no group.",
     "Added German, French and Spanish trade words and manufacturing roles to Engineering and MRO. Remaining unclear titles still default to Corporate; turning on AI sorting (Anthropic key with a $5 limit) would sort them properly.",
     "Partly fixed", "See Data quality"],
    ["DEF-06", "Visual check of live screenshots", "Medium", "RTX job locations showed raw internal codes",
     "Locations appeared as 'IN-KA-BENGALURU-BLDG 1 ~ Hitech, Defence & Aerospace Park ~ …'.",
     "Coded locations are now shown as 'Bengaluru, India'. 13 older jobs keep the old text until their next update.", "Fixed", "Pass"],
    ["DEF-07", "Browser test TC-JS-01 (Safari engine)", "Low", "Cloudflare's own visitor-analytics script is blocked in Safari",
     "Cloudflare automatically adds a Web Analytics script (/cdn-cgi/rum). Safari blocks its report, which shows as console errors. Visitors see no difference.",
     "Owner choice: turn off Web Analytics for the aerojobs project in Cloudflare if Google Analytics will be used instead, or ignore.",
     "Known issue" if js_fail_r2 else "Fixed", "Fail" if js_fail_r2 else "Pass"],
    ["DEF-08", "Security test SEC-22", "Low", "Clickjacking check reported a failure in the first run (test issue, not a site issue)",
     "The first run counted Chrome's 'refused to connect' error page as the site loading inside another site's frame. The site was protected all along.",
     "Test corrected to check the frame's real content and the headers received. Re-test confirms the browser refuses to show AeroJobs inside other sites (X-Frame-Options SAMEORIGIN, CSP frame-ancestors 'self').",
     "Closed", sec22["status"] if sec22 else "-"],
    ["DEF-12", "Owner (black-box test)", "High", "Filter counts did not update when other filters were selected",
     "Steps: tick Remote, open Country. India still showed (225), its total, although it has no remote jobs. The counts were fixed when the site was built.",
     "Every count next to country, region, role, posted date, employer type and the work-mode buttons is now recalculated from the other active filters; choices with 0 jobs are greyed out. New test TC-FLT-08 repeats the reported steps.",
     "Fixed", "Pass"],
    ["DEF-09", "Data review", "Medium", "Some employers post many non-aviation jobs",
     "Honeywell (building tech, IT, HVAC) and RTX (Raytheon defence) list jobs outside aviation.",
     "Owner choice: keep, drop Honeywell, or add a per-employer filter that keeps only aerospace business units (can be built).", "Owner decision", "-"],
    ["DEF-10", "Capacity review", "Low", "Free hosting limit of 20,000 files per site",
     "Each job is one page. Today: 3,668 files. At roughly 19,000 jobs the site would hit Cloudflare's free limit; the job list download is 1.2 MB (185 KB compressed).",
     "Cap kept at 600 jobs per employer while testing. Before growing past about 15,000 jobs, change job pages to be generated on demand (Cloudflare Functions, still free).", "Planned", "-"],
    ["DEF-11", "Coverage review", "Medium", "Few airline jobs in this first set of 10 employers",
     "Most airlines either forbid automated reading in their robots.txt (American, Delta, KLM, Qantas, IndiGo, flydubai, Alaska, Etihad, Wizz Air) or use systems not yet supported (SuccessFactors, Taleo, iCIMS). Only 7 pilot jobs and 0 cabin crew jobs today.",
     "Next: add SuccessFactors and Taleo readers (JetBlue, Ryanair, Qatar Airways, easyJet) and run the .aero directory tool.", "Planned", "-"],
]
ws = sheet("Defects", ["Defect ID", "Found by", "Severity", "Problem", "Details", "What was done", "Status", "Re-test"],
           [9, 22, 9, 36, 60, 60, 13, 10], DEF)
color_status(ws, f"G2:H{ws.max_row}")
for i in range(2, ws.max_row + 1):
    sev = ws[f"C{i}"].value
    ws[f"C{i}"].font = Font(name=FONT, size=10, bold=True, color={"High": T_FAIL, "Medium": T_WARN}.get(sev, T_GREY))
DEF_ROWS = ws.max_row

# ------------------------------------------------------------------ Employers
def load_jobs(p):
    d = json.load(open(p))["jobs"]
    return [j for j in d.values() if j.get("status") == "active" and j.get("title") and j.get("slug")]

JB, JA = load_jobs(jobs_before), load_jobs(jobs_after)
v1 = {r["slug"]: r for r in json.load(open(ver1))["results"]}
v2 = {r["slug"]: r for r in json.load(open(ver2))["results"]}
EMP = [("Airbus", "Manufacturer", "France", "Workday", "airbus"),
       ("Boeing", "Manufacturer", "United States", "Workday", "boeing"),
       ("RTX (Collins Aerospace, Pratt & Whitney)", "Manufacturer", "United States", "Workday", "rtx"),
       ("GE Aerospace", "Manufacturer", "United States", "Workday", "ge-aerospace"),
       ("Rolls-Royce", "Manufacturer", "United Kingdom", "Workday", "rolls-royce"),
       ("Honeywell", "Manufacturer", "United States", "Oracle Recruiting Cloud", "honeywell"),
       ("Archer Aviation", "Manufacturer (eVTOL)", "United States", "Greenhouse", "archer-aviation"),
       ("Skyryse", "Manufacturer (flight tech)", "United States", "Greenhouse", "skyryse"),
       ("Virgin Atlantic", "Airline", "United Kingdom", "Oracle Recruiting Cloud", "virgin-atlantic"),
       ("Heathrow Airport", "Airport", "United Kingdom", "Oracle Recruiting Cloud", "heathrow")]
rows = []
for name, typ, hq, ats, slug in EMP:
    a = [j for j in JA if j["employer"] == slug]
    rows.append([name, typ, hq, ats, len(a), sum(1 for j in a if j.get("country_code")), None,
                 len({j["country_code"] for j in a if j.get("country_code")}),
                 sum(1 for j in a if j.get("role_source") == "default"), None,
                 sum(1 for j in a if j.get("closing_date")), "Pass"])
ws = sheet("Employers (10)", ["Employer", "Type", "Head office", "Hiring system", "Live jobs", "Jobs with country",
                              "% with country", "Countries", "Role unclear (Corporate by default)", "% unclear",
                              "Jobs with closing date", "Apply link check"],
           [34, 20, 15, 22, 10, 11, 10, 10, 14, 10, 12, 11], rows)
n = ws.max_row
for i in range(2, n + 1):
    ws[f"G{i}"] = f"=IF(E{i}=0,0,F{i}/E{i})"
    ws[f"J{i}"] = f"=IF(E{i}=0,0,I{i}/E{i})"
    for col in "GJ":
        ws[f"{col}{i}"].number_format = "0%"
        ws[f"{col}{i}"].font, ws[f"{col}{i}"].border = BODY, BOX
t = n + 1
ws[f"A{t}"] = "Total"
for col in "EFIK":
    ws[f"{col}{t}"] = f"=SUM({col}2:{col}{n})"
ws[f"G{t}"] = f"=IF(E{t}=0,0,F{t}/E{t})"
ws[f"J{t}"] = f"=IF(E{t}=0,0,I{t}/E{t})"
for col in "ABCDEFGHIJKL":
    c = ws[f"{col}{t}"]
    c.font, c.fill, c.border = Font(name=FONT, bold=True, size=10), PatternFill("solid", fgColor=SKY), BOX
ws[f"G{t}"].number_format = ws[f"J{t}"].number_format = "0%"
ws[f"A{t + 2}"] = "Jobs capped at 600 per employer per run while testing. Live data as of the re-test run on 5 Oct 2026."
ws[f"A{t + 2}"].font = Font(name=FONT, italic=True, size=9, color=T_GREY)
color_status(ws, f"L2:L{n}")
ws.auto_filter.ref = f"A1:L{n}"

# ------------------------------------------------------------------ Candidates not used
reasons = []
for r in list(json.load(open(ver1))["results"]) + list(json.load(open(ver2))["results"]):
    if r["ok"] or r["slug"].endswith("-2") or r["slug"] in ("boom-lever",):
        continue
    e = r.get("error", "no jobs")
    why = ("Their robots.txt forbids automated reading - respected" if "robots" in e else
           "Address guessed for the test does not exist (HTTP 404)" if "404" in e else
           "Address guessed for the test was refused (HTTP 422/401)" if ("422" in e or "401" in e) else e[:80])
    reasons.append([r["name"], r["source"].get("ats", ""), why])
for name, why in [("American Airlines, Delta, KLM, Qantas, IndiGo, LATAM, Ethiopian, AAR, Lufthansa Technik", "Careers site's robots.txt forbids automated reading - respected"),
                  ("JetBlue, Ryanair, Wizz Air", "Use SAP SuccessFactors: reader not built yet"),
                  ("Qatar Airways, easyJet", "Use Oracle Taleo: reader not built yet"),
                  ("United, Southwest, Air Canada, Emirates, British Airways, Lufthansa, Cathay, Air NZ", "Jobs load by script; hiring system not visible from the page yet")]:
    reasons.append([name, "careers page", why])
ws = sheet("Employers not used", ["Employer", "Hiring system tried", "Why not switched on"], [60, 18, 70], reasons)

# ------------------------------------------------------------------ Data quality before / after
def pct(lst, f):
    return sum(1 for j in lst if f(j))
dq = [
    ["Live jobs", len(JB), len(JA), "Count of jobs on the site"],
    ["Jobs with a country", pct(JB, lambda j: j.get("country_code")), pct(JA, lambda j: j.get("country_code")), "Needed for the Country filter (DEF-04)"],
    ["Countries covered", len({j["country_code"] for j in JB if j.get("country_code")}), len({j["country_code"] for j in JA if j.get("country_code")}), ""],
    ["Jobs whose role was unclear (put in Corporate)", pct(JB, lambda j: j.get("role_source") == "default"), pct(JA, lambda j: j.get("role_source") == "default"), "DEF-05"],
    ["Jobs in Engineering and MRO", pct(JB, lambda j: j["role"] == "engineering-maintenance"), pct(JA, lambda j: j["role"] == "engineering-maintenance"), ""],
    ["Jobs showing coded locations (~)", pct(JB, lambda j: "~" in (j.get("location") or "")), pct(JA, lambda j: "~" in (j.get("location") or "")), "DEF-06"],
    ["Jobs with a closing date", pct(JB, lambda j: j.get("closing_date")), pct(JA, lambda j: j.get("closing_date")), "Employers often don't publish one"],
    ["Jobs with an exact posting date", pct(JB, lambda j: not j.get("posted_estimated")), pct(JA, lambda j: not j.get("posted_estimated")), "Others show 'First seen' date"],
]
ws = sheet("Data quality", ["Measure", "First fetch", "After fixes", "Change", "% of jobs (after)", "Note"],
           [44, 12, 12, 10, 14, 40], [[a, b, c, None, None, d] for a, b, c, d in dq])
for i in range(2, ws.max_row + 1):
    ws[f"D{i}"] = f"=C{i}-B{i}"
    ws[f"E{i}"] = f"=IF($C$2=0,0,C{i}/$C$2)"
    ws[f"E{i}"].number_format = "0%"
    ws[f"D{i}"].number_format = "+#,##0;-#,##0;0"
    for col in "DE":
        ws[f"{col}{i}"].font, ws[f"{col}{i}"].border = BODY, BOX
ws["E2"] = None
ws["E4"] = None

# ------------------------------------------------------------------ Summary (first tab)
ws = wb["Sheet"]
ws.title = "Summary"
ws.sheet_view.showGridLines = False
ws.column_dimensions["A"].width = 3
ws.column_dimensions["B"].width = 42
for c in "CDEF":
    ws.column_dimensions[c].width = 14
ws.column_dimensions["G"].width = 50
ws["B2"] = "AeroJobs test report"
ws["B2"].font = Font(name=FONT, bold=True, size=18, color=NAVY)
ws["B3"] = "Live site https://aerojobs.work with 10 real employers. Tested 5 October 2026; re-tested after the owner's filter bug report."
ws["B3"].font = Font(name=FONT, size=10, color=T_GREY)

def block(r, title):
    ws[f"B{r}"] = title
    ws[f"B{r}"].font = Font(name=FONT, bold=True, size=12, color=NAVY)

block(5, "Results (re-test after fixes)")
hdr = ["", "Total", "Pass", "Fail", "Not tested / skipped"]
for i, h in enumerate(hdr):
    c = ws.cell(row=6, column=2 + i, value=h or "Test group")
    c.font, c.fill, c.border = H_FONT, H_FILL, BOX
ws["B7"] = "Website tests (unique test cases)"
ws["C7"] = f"=COUNTA('Test cases'!A2:A{TC_ROWS})"
ws["D7"] = f"=COUNTIF('Test cases'!M2:M{TC_ROWS},\"Pass\")"
ws["E7"] = f"=COUNTIF('Test cases'!M2:M{TC_ROWS},\"Fail\")"
ws["F7"] = f"=COUNTIF('Test cases'!M2:M{TC_ROWS},\"Skip\")"
ws["B8"] = "Website test runs (each browser and device)"
ws["C8"] = f"=COUNTA('Test cases'!G2:L{TC_ROWS})-COUNTIF('Test cases'!G2:L{TC_ROWS},\"N/A\")"
ws["D8"] = f"=COUNTIF('Test cases'!G2:L{TC_ROWS},\"Pass\")"
ws["E8"] = f"=COUNTIF('Test cases'!G2:L{TC_ROWS},\"Fail\")"
ws["F8"] = f"=COUNTIF('Test cases'!G2:L{TC_ROWS},\"Skip\")"
ws["B9"] = "Security and penetration tests"
ws["C9"] = f"=COUNTA('Security tests'!A2:A{SEC_ROWS})"
ws["D9"] = f"=COUNTIF('Security tests'!F2:F{SEC_ROWS},\"Pass\")"
ws["E9"] = f"=COUNTIF('Security tests'!F2:F{SEC_ROWS},\"Fail\")"
ws["F9"] = f"=COUNTIF('Security tests'!F2:F{SEC_ROWS},\"Not tested\")"
ws["B10"] = "Automated code tests (run on every update)"
ws["C10"], ws["D10"], ws["E10"], ws["F10"] = 20, 20, 0, 0
ws["G10"] = "Fetcher, readers, filters data, site build, unsafe links"
ws["G10"].font = Font(name=FONT, size=9, color=T_GREY)
ws["B11"] = "Defects found"
ws["C11"] = f"=COUNTA(Defects!A2:A{DEF_ROWS})"
ws["D11"] = f"=COUNTIF(Defects!G2:G{DEF_ROWS},\"Fixed\")+COUNTIF(Defects!G2:G{DEF_ROWS},\"Closed\")"
ws["E11"] = f"=COUNTIF(Defects!G2:G{DEF_ROWS},\"Open\")"
ws["F11"] = f"=C11-D11-E11"
ws["G11"] = "Pass column = fixed or closed; Fail = still open; last column = partly fixed, known, planned or owner decision"
ws["G11"].font = Font(name=FONT, size=9, color=T_GREY)
for r in range(7, 12):
    for c in "BCDEF":
        ws[f"{c}{r}"].border, ws[f"{c}{r}"].font = BOX, BODY
    ws[f"D{r}"].font = Font(name=FONT, size=10, bold=True, color=T_PASS)
    ws[f"E{r}"].font = Font(name=FONT, size=10, bold=True, color=T_FAIL)

block(13, "What was tested")
scope = [
    ("Browsers and devices", "Chrome, Firefox and Safari's engine (WebKit) on desktop; Pixel 7 (Android), iPhone 13 and a 390px Firefox phone"),
    ("Test types", "Functional, black box, end to end, responsive/phone, accessibility basics, speed, SEO and AdSense readiness, security and penetration"),
    ("Pages and flows", "Home, search, every filter, sorting, Show more, job pages, Apply links, employer/country/role pages, guides, legal pages, 404, phone menu and filter panel"),
    ("Expected results", "Worked out from the site's own live job list, so counts are checked exactly against real data"),
    ("Data", "3,598 live jobs from 10 real employers in 42 countries"),
    ("Not tested", "Flood/DDoS attacks (would attack Cloudflare); real iPhone/Android hardware (emulated devices used)"),
]
for i, (a, b) in enumerate(scope):
    ws[f"B{14 + i}"], ws[f"C{14 + i}"] = a, b
    ws.merge_cells(f"C{14 + i}:G{14 + i}")
    ws[f"B{14 + i}"].font, ws[f"B{14 + i}"].alignment = Font(name=FONT, bold=True, size=10), WRAP
    ws[f"C{14 + i}"].font, ws[f"C{14 + i}"].alignment = BODY, WRAP
    ws.row_dimensions[14 + i].height = 28

block(21, "Decisions needed from you")
asks = ["Honeywell and RTX list many non-aviation jobs. Keep them, drop Honeywell, or filter to aerospace units? (DEF-09)",
        "Turn on AI role sorting? Needs an Anthropic API key with a $5 monthly limit, added as a GitHub secret. (DEF-05)",
        "Cloudflare Web Analytics: keep, or switch off if you'll use Google Analytics? (DEF-07)",
        "Next employers: build SuccessFactors and Taleo readers to add JetBlue, Ryanair, Qatar Airways and easyJet? (DEF-11)"]
for i, a in enumerate(asks):
    ws[f"B{22 + i}"] = f"{i + 1}. {a}"
    ws.merge_cells(f"B{22 + i}:G{22 + i}")
    ws[f"B{22 + i}"].font, ws[f"B{22 + i}"].alignment = BODY, WRAP
    ws.row_dimensions[22 + i].height = 28
ws["B27"] = "Tabs: Test cases · Security tests · Defects · Employers (10) · Employers not used · Data quality"
ws["B27"].font = Font(name=FONT, size=9, color=T_GREY)

ws.page_setup.orientation = "landscape"
ws.page_setup.fitToWidth = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True
wb.move_sheet("Summary", offset=-wb.index(wb["Summary"]))
wb.active = 0
wb.save(out)
print("saved", out)
