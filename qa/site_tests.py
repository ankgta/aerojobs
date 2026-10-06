"""Black-box, functional and end-to-end tests for the AeroJobs website.

    python qa/site_tests.py --base https://aerojobs.work --browsers chromium,firefox,webkit --out qa-results

Tests the site the way a visitor uses it, through a real browser. The expected results
are worked out from the site's own public job list (/data/jobs-index.json), so the tests
work with whatever jobs are live today. Writes results.json and screenshots to --out.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import traceback
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext

RESULTS: list[dict] = []
OUT = Path("qa-results")


class Skip(Exception):
    pass


def record(tc, area, kind, title, steps, expected, browser, device, status, actual, evidence=""):
    RESULTS.append({"id": tc, "area": area, "type": kind, "title": title, "steps": steps,
                    "expected": expected, "browser": browser, "device": device,
                    "status": status, "actual": actual, "evidence": evidence})
    mark = {"Pass": "✓", "Fail": "✗", "Skip": "-"}[status]
    print(f"  {mark} {tc} [{browser}/{device}] {title}: {actual[:140]}", flush=True)


def run_case(ctx_info, tc, area, kind, title, steps, expected, fn, *args):
    browser, device, page = ctx_info
    try:
        actual = fn(page, *args)
        record(tc, area, kind, title, steps, expected, browser, device, "Pass", actual or "As expected")
    except Skip as e:
        record(tc, area, kind, title, steps, expected, browser, device, "Skip", str(e))
    except Exception as e:
        shot = OUT / "screens" / f"{tc}-{browser}-{device}.png"
        try:
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot))
        except Exception:
            shot = None
        msg = str(e).strip().splitlines()[0][:300] if str(e).strip() else type(e).__name__
        record(tc, area, kind, title, steps, expected, browser, device, "Fail", msg,
               str(shot.relative_to(OUT)) if shot else "")


# ------------------------------------------------------------------ helpers
def today_utc() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def days_ago(iso: str) -> int:
    return (today_utc() - dt.date.fromisoformat(iso)).days


def count_on_page(page: Page) -> int:
    text = page.locator("[data-count]").inner_text()
    m = re.search(r"([\d,]+)", text)
    assert m, f"count text not understood: {text!r}"
    return int(m.group(1).replace(",", ""))


def wait_ready(page: Page):
    page.wait_for_function("() => { const c = document.querySelector('[data-count]'); return c && /\\d/.test(c.textContent) && !/Refresh/.test(c.textContent); }", timeout=15000)
    page.wait_for_timeout(250)


def goto(page: Page, base: str, path: str = "/"):
    r = page.goto(base.rstrip("/") + path, wait_until="domcontentloaded")
    return r


def open_filters_if_sheet(page: Page):
    btn = page.locator("[data-sheet-open]")
    if btn.is_visible():
        btn.click()
        page.wait_for_timeout(400)


def close_filters_if_sheet(page: Page):
    sheet = page.locator("[data-sheet]")
    if "is-open" in (sheet.get_attribute("class") or ""):
        page.locator(".sheet-apply").click()
        page.wait_for_timeout(400)


def set_select(page: Page, sel: str, value: str):
    open_filters_if_sheet(page)
    page.select_option(sel, value)
    page.wait_for_timeout(150)


def visible_cards(page: Page):
    return page.locator("[data-results] .job-card")


# ------------------------------------------------------------------ test bodies
def t_home_loads(page, base, index):
    r = goto(page, base)
    assert r and r.status == 200, f"HTTP {r.status if r else 'no response'}"
    h1 = page.locator("h1").inner_text()
    assert "Every aviation job" in h1, f"headline was {h1!r}"
    assert "AeroJobs" in page.title(), f"title was {page.title()!r}"
    wait_ready(page)
    n = count_on_page(page)
    assert n == len(index), f"page says {n} jobs, data has {len(index)}"
    return f"HTTP 200, headline shown, {n} jobs listed (matches data)"


def t_header_links(page, base, index):
    goto(page, base)
    names = []
    for label, path in (("Employers", "/companies/"), ("Countries", "/countries/"), ("Guides", "/guides/")):
        goto(page, base)
        menu = page.locator("[data-menu]")
        if menu.is_visible():
            menu.click()
        page.locator("#top-nav a", has_text=label).click()
        page.wait_for_load_state("domcontentloaded")
        assert urllib.parse.urlsplit(page.url).path.rstrip("/").endswith(path.rstrip("/")), f"{label} went to {page.url}"
        assert page.locator("h1").count() == 1
        names.append(label)
    goto(page, base, "/companies/")
    page.locator("a.brand").first.click()
    page.wait_for_load_state("domcontentloaded")
    assert urllib.parse.urlsplit(page.url).path in ("/", "/index.html"), f"logo went to {page.url}"
    return f"{', '.join(names)} open the right pages; logo returns home"


def t_role_chips(page, base, index):
    goto(page, base)
    hrefs = page.locator(".hero .chips a.chip").evaluate_all("els => els.map(e => e.getAttribute('href'))")
    assert len(hrefs) == 8, f"found {len(hrefs)} role chips"
    for h in hrefs:
        r = page.goto(urllib.parse.urljoin(base + "/", h))
        assert r.status == 200, f"{h}: HTTP {r.status}"
        assert page.locator("h1").inner_text().endswith("jobs")
    return "All 8 role chips open their role page (HTTP 200)"


def t_footer_pages(page, base, index):
    out = []
    for path, must in (("/about/", "About"), ("/contact/", "hello@aerojobs.work"), ("/privacy/", "Google"),
                       ("/terms/", "never charge")):
        r = goto(page, base, path)
        assert r.status == 200, f"{path}: HTTP {r.status}"
        body = page.locator("main").inner_text()
        assert must.lower() in body.lower(), f"{path} does not mention {must!r}"
        out.append(path)
    return "About, Contact (email shown), Privacy (mentions Google ads), Terms all load"


def t_404(page, base, index):
    r = goto(page, base, "/this-page-does-not-exist-12345/")
    assert r.status == 404, f"HTTP {r.status}, expected 404"
    assert "left the gate" in page.locator("h1").inner_text()
    return "HTTP 404 with the friendly 'left the gate' page and a link back"


def t_broken_links(page, base, index):
    """Crawl every internal link reachable from the home page and check none is broken."""
    host = urllib.parse.urlsplit(base).netloc
    seen, todo, bad, checked = set(), ["/"], [], 0
    req = page.request
    while todo and checked < 700:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        r = req.get(base.rstrip("/") + path, max_redirects=3)
        checked += 1
        if r.status >= 400:
            bad.append(f"{path} -> {r.status}")
            continue
        if "text/html" not in r.headers.get("content-type", ""):
            continue
        for href in re.findall(r'href="([^"#]+)', r.text()):
            u = urllib.parse.urlsplit(urllib.parse.urljoin(base.rstrip("/") + path, href))
            if u.netloc == host and u.path not in seen:
                todo.append(u.path)
    assert not bad, f"{len(bad)} broken: {bad[:5]}"
    return f"Crawled {checked} pages and files; no broken internal links"


def t_search_title(page, base, index):
    word = None
    for w in ("engineer", "pilot", "technician", "manager", "analyst", "mechanic", "specialist"):
        if sum(w in j["t"].lower() for j in index) >= 2:
            word = w
            break
    if not word:
        raise Skip("no common title word in today's data")
    goto(page, base)
    wait_ready(page)
    page.fill("#q", word.upper())
    page.locator("form[data-search-form] button").click()
    page.wait_for_timeout(400)
    expected = sum(word in (j["t"] + " " + j["c"] + " " + j["l"] + " " + j["cn"]).lower() for j in index)
    n = count_on_page(page)
    assert n == expected, f"searching {word!r}: page shows {n}, expected {expected}"
    titles = visible_cards(page).locator(".job-card .job-title, .job-title").all_inner_texts()[:25]
    return f"Search '{word.upper()}' (upper case) found {n} jobs, matching the data; case-insensitive"


def t_search_employer(page, base, index):
    company = index[0]["c"]
    goto(page, base)
    wait_ready(page)
    page.fill("#q", company)
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    expected = sum(company.lower() in (j["t"] + " " + j["c"] + " " + j["l"] + " " + j["cn"]).lower() for j in index)
    n = count_on_page(page)
    assert n == expected, f"page shows {n}, expected {expected}"
    companies = set(visible_cards(page).locator(".job-meta span").first.all_inner_texts())
    return f"Search '{company}' with Enter key found {n} jobs, matching the data"


def t_search_none(page, base, index):
    goto(page, base)
    wait_ready(page)
    page.fill("#q", "zzqqxx-no-such-job")
    page.wait_for_timeout(300)
    assert page.locator("[data-empty]").is_visible(), "empty message not shown"
    assert visible_cards(page).count() == 0
    assert page.locator("[data-more]").is_hidden()
    page.fill("#q", "")
    page.wait_for_timeout(300)
    assert count_on_page(page) == len(index), "clearing the search did not restore all jobs"
    return "No-match search shows the 'No jobs match' message; clearing it restores all jobs"


def t_filter_country(page, base, index):
    counts = {}
    for j in index:
        if j["cc"]:
            counts[j["cc"]] = counts.get(j["cc"], 0) + 1
    if not counts:
        raise Skip("no countries in data")
    cc = max(counts, key=counts.get)
    goto(page, base)
    wait_ready(page)
    set_select(page, "#f-country", cc)
    close_filters_if_sheet(page)
    n = count_on_page(page)
    assert n == counts[cc], f"{cc}: page {n}, data {counts[cc]}"
    region = next(j["rg"] for j in index if j["cc"] == cc)
    set_select(page, "#f-country", f"region:{region}")
    close_filters_if_sheet(page)
    exp_r = sum(j["rg"] == region for j in index)
    assert count_on_page(page) == exp_r, f"region {region}: page {count_on_page(page)}, data {exp_r}"
    return f"Country {cc}: {n} jobs; region {region}: {exp_r} jobs; both match the data"


def t_filter_role(page, base, index):
    goto(page, base)
    wait_ready(page)
    roles = sorted({j["r"] for j in index})
    out = []
    for r in roles:
        set_select(page, "#f-role", r)
        close_filters_if_sheet(page)
        exp = sum(j["r"] == r for j in index)
        n = count_on_page(page)
        assert n == exp, f"role {r}: page {n}, data {exp}"
        out.append(f"{r}={n}")
    return "Each role matches the data: " + ", ".join(out)


def t_filter_mode(page, base, index):
    goto(page, base)
    wait_ready(page)
    out = []
    for mode in ("On-site", "Hybrid", "Remote"):
        open_filters_if_sheet(page)
        page.locator(f"label.toggle:has(#f-mode-{mode.lower()})").click()
        close_filters_if_sheet(page)
        exp = sum(j["w"] == mode for j in index)
        n = count_on_page(page)
        assert n == exp, f"{mode}: page {n}, data {exp}"
        out.append(f"{mode}={n}")
        open_filters_if_sheet(page)
        page.locator(f"label.toggle:has(#f-mode-{mode.lower()})").click()
        close_filters_if_sheet(page)
    open_filters_if_sheet(page)
    page.locator("label.toggle:has(#f-mode-hybrid)").click()
    page.locator("label.toggle:has(#f-mode-remote)").click()
    close_filters_if_sheet(page)
    exp = sum(j["w"] in ("Hybrid", "Remote") for j in index)
    assert count_on_page(page) == exp, "Hybrid+Remote together wrong"
    return "Single modes " + ", ".join(out) + f"; Hybrid+Remote together = {exp}"


def t_filter_posted(page, base, index):
    goto(page, base)
    wait_ready(page)
    out = []
    for v, label in (("1", "24h"), ("2", "48h"), ("7", "week"), ("30", "month"), ("older", ">month")):
        set_select(page, "#f-posted", v)
        close_filters_if_sheet(page)
        exp = sum((days_ago(j["p"]) > 30) if v == "older" else (days_ago(j["p"]) <= int(v)) for j in index)
        n = count_on_page(page)
        assert n == exp, f"{label}: page {n}, data {exp}"
        out.append(f"{label}={n}")
    return "Posted-date filters match the data: " + ", ".join(out)


def t_filter_type(page, base, index):
    goto(page, base)
    wait_ready(page)
    types = sorted({j["ct"] for j in index})
    out = []
    for t in types:
        set_select(page, "#f-type", t)
        close_filters_if_sheet(page)
        exp = sum(j["ct"] == t for j in index)
        assert count_on_page(page) == exp, f"{t}: page {count_on_page(page)}, data {exp}"
        out.append(f"{t}={exp}")
    return "Employer types match: " + ", ".join(out)


def t_filter_combined_and_clear(page, base, index):
    j0 = next((j for j in index if j["cc"]), None)
    if not j0:
        raise Skip("no data")
    goto(page, base)
    wait_ready(page)
    set_select(page, "#f-country", j0["cc"])
    set_select(page, "#f-role", j0["r"])
    page.locator(f"label.toggle:has(#f-mode-{j0['w'].lower()})").click()
    close_filters_if_sheet(page)
    exp = sum(j["cc"] == j0["cc"] and j["r"] == j0["r"] and j["w"] == j0["w"] for j in index)
    n = count_on_page(page)
    assert n == exp, f"combined: page {n}, data {exp}"
    open_filters_if_sheet(page)
    page.locator("[data-reset]").click()
    close_filters_if_sheet(page)
    assert count_on_page(page) == len(index), "Clear all did not restore every job"
    assert page.locator("#f-country").input_value() == "" and page.locator("#f-role").input_value() == ""
    return f"Country+role+mode together = {n} (matches); Clear all restores {len(index)}"


def option_counts(page, sel):
    return page.evaluate(f"""[...document.querySelectorAll('{sel} option')].filter(o => o.value)
        .map(o => [o.value, o.textContent, o.disabled])""")


def t_live_counts(page, base, index):
    """Owner's bug report: with Remote ticked, 'India (225)' must change to India's remote count."""
    goto(page, base)
    wait_ready(page)
    open_filters_if_sheet(page)
    page.locator("label.toggle:has(#f-mode-remote)").click()
    page.wait_for_timeout(250)
    remote = [j for j in index if j["w"] == "Remote"]
    bad, zero_disabled = [], 0
    for value, text, disabled in option_counts(page, "#f-country"):
        exp = sum(1 for j in remote if (j["rg"] == value[7:] if value.startswith("region:") else j["cc"] == value))
        m = re.search(r"\(([\d,]+)\)$", text)
        got = int(m.group(1).replace(",", "")) if m else None
        if got != exp:
            bad.append(f"{text!r} expected ({exp})")
        if exp == 0:
            zero_disabled += disabled
            if not disabled:
                bad.append(f"{text!r} should be greyed out")
    for value, text, disabled in option_counts(page, "#f-role"):
        exp = sum(1 for j in remote if j["r"] == value)
        if not text.endswith(f"({exp:,})"):
            bad.append(f"role {text!r} expected ({exp})")
    # and the other way round: pick the busiest country, the Remote button count must follow
    page.locator("label.toggle:has(#f-mode-remote)").click()
    cc = max({j["cc"] for j in index if j["cc"]}, key=lambda c: sum(j["cc"] == c for j in index))
    page.select_option("#f-country", cc)
    page.wait_for_timeout(250)
    exp_remote = sum(1 for j in index if j["cc"] == cc and j["w"] == "Remote")
    label = page.locator("label.toggle:has(#f-mode-remote) span").inner_text()
    if not label.endswith(f"({exp_remote:,})"):
        bad.append(f"Remote button says {label!r}, expected ({exp_remote}) for {cc}")
    close_filters_if_sheet(page)
    assert not bad, "; ".join(bad[:5])
    return (f"With Remote ticked every country, region and role count matches the remote jobs; {zero_disabled} countries "
            f"with no remote jobs are greyed out; with {cc} picked the Remote button shows ({exp_remote})")


def t_url_state(page, base, index):
    j0 = index[0]
    goto(page, base, f"/?role={j0['r']}&mode={urllib.parse.quote(j0['w'])}&sort=closing#jobs")
    wait_ready(page)
    exp = sum(j["r"] == j0["r"] and j["w"] == j0["w"] for j in index)
    n = count_on_page(page)
    assert n == exp, f"shared link: page {n}, data {exp}"
    assert page.locator("#f-sort").input_value() == "closing"
    page.reload()
    wait_ready(page)
    assert count_on_page(page) == exp, "reload lost the filters"
    return f"A shared link with filters opens with them applied ({n} jobs) and survives reload"


def t_sort(page, base, index):
    goto(page, base)
    wait_ready(page)
    # newest first: the first 25 cards must be in non-increasing posted order
    exp_new = sorted(index, key=lambda j: j["p"], reverse=True)[:25]
    by_path = {j["u"]: j for j in index}
    hrefs = visible_cards(page).locator(".job-title").evaluate_all("els => els.map(e => e.getAttribute('href'))")[:25]
    dates_shown = [by_path[h.strip("/").split("/index.html")[0].lstrip("./")]["p"] for h in hrefs]
    assert dates_shown == sorted(dates_shown, reverse=True), "newest-first order is wrong"
    page.select_option("#f-sort", "closing")
    page.wait_for_timeout(300)
    with_close = sorted([j for j in index if j["x"]], key=lambda j: j["x"])
    first_href = visible_cards(page).locator(".job-title").first.get_attribute("href")
    first_job = by_path[first_href.strip("/").split("/index.html")[0].lstrip("./")]
    first = first_job["t"]
    if with_close:
        assert first_job["x"] == with_close[0]["x"], f"closing-soonest first card closes {first_job['x']!r}, expected {with_close[0]['x']}"
        return f"Newest-first order correct; Closing-soonest puts {first!r} (closes {with_close[0]['x']}) first"
    return "Newest-first order correct; no closing dates in data, so closing sort falls back to newest"


def t_show_more(page, base, index):
    if len(index) <= 25:
        raise Skip(f"only {len(index)} jobs; 'Show more' needs over 25")
    goto(page, base)
    wait_ready(page)
    assert visible_cards(page).count() == 25
    page.locator("[data-more]").click()
    page.wait_for_timeout(300)
    n2 = visible_cards(page).count()
    assert n2 == min(50, len(index)), f"after one click {n2} cards"
    clicks = 0
    while page.locator("[data-more]").is_visible() and clicks < 200:
        page.locator("[data-more]").click()
        clicks += 1
    assert visible_cards(page).count() == len(index)
    assert page.locator("[data-more]").is_hidden(), "'Show more' button still visible after every job is shown"
    return f"Shows 25, then 50 after 'Show more'; button disappears after all {len(index)} are shown"


def t_job_page(page, base, index):
    j = index[0]
    r = goto(page, base, f"/{j['u']}/")
    assert r.status == 200, f"HTTP {r.status}"
    assert page.locator("h1").inner_text().strip() == j["t"]
    body = page.locator("main").inner_text()
    assert j["c"] in body and ("Posted" in body or "First seen" in body) and "Closes" in body
    a = page.locator(".apply-card a.btn, .apply-bar a.btn").first
    href, target, rel = a.get_attribute("href"), a.get_attribute("target"), a.get_attribute("rel") or ""
    assert href.startswith("https://"), f"apply link not https: {href}"
    assert target == "_blank" and "noopener" in rel, "apply link must open in a new tab with noopener"
    return f"Job page shows title, employer, dates; Apply goes to {urllib.parse.urlsplit(href).netloc} in a new tab"


def t_jsonld(page, base, index):
    bad, n = [], 0
    for j in index[:15]:
        goto(page, base, f"/{j['u']}/")
        raw = page.locator('script[type="application/ld+json"]').all_inner_texts()
        if not raw:
            bad.append(f"{j['u']}: none")
            continue
        d = json.loads(raw[0])
        n += 1
        for k in ("title", "datePosted", "hiringOrganization", "description"):
            if not d.get(k):
                bad.append(f"{j['u']}: missing {k}")
        if not d.get("jobLocation") and d.get("jobLocationType") != "TELECOMMUTE":
            bad.append(f"{j['u']}: no location")
    assert not bad, "; ".join(bad[:4])
    return f"Google for Jobs data present and complete on {n} sampled job pages"


def t_apply_links_live(page, base, index):
    """One job per employer: the Apply link must reach a working page on the employer's site."""
    seen, out, bad = set(), [], []
    for j in index:
        if j["cs"] in seen:
            continue
        seen.add(j["cs"])
        goto(page, base, f"/{j['u']}/")
        href = page.locator(".apply-card a.btn, .apply-bar a.btn").first.get_attribute("href")
        try:
            r = page.request.get(href, max_redirects=5, timeout=30000)
            status = r.status
        except Exception as e:
            status = f"error {type(e).__name__}"
        host = urllib.parse.urlsplit(href).netloc
        (out if isinstance(status, int) and status < 400 else bad).append(f"{j['c']}: {status} ({host})")
    assert not bad, "; ".join(bad)
    return f"Apply links reach the employer for all {len(out)} employers: " + "; ".join(out)


def t_breadcrumbs_similar(page, base, index):
    j = index[0]
    goto(page, base, f"/{j['u']}/")
    links = page.locator(".crumbs a").evaluate_all("els => els.map(e => e.getAttribute('href'))")
    assert len(links) == 3
    for h in links:
        r = page.request.get(urllib.parse.urljoin(page.url, h.split("#")[0]))
        assert r.status == 200, f"{h}: {r.status}"
    sim = page.locator(".similar .job-title")
    if sim.count():
        sim.first.click()
        page.wait_for_load_state("domcontentloaded")
        assert page.locator("h1").count() == 1
    return f"3 breadcrumb links work; {sim.count()} similar jobs listed and clickable"


def t_company_page(page, base, index):
    slug = index[0]["cs"]
    exp = sum(j["cs"] == slug for j in index)
    r = goto(page, base, f"/companies/{slug}/")
    assert r.status == 200
    shown = page.locator(".job-card").count()
    assert shown == min(exp, 100), f"company page shows {shown}, data {exp}"
    link = page.locator(".see-more a").first
    link.click()
    page.wait_for_load_state("domcontentloaded")
    wait_ready(page)
    assert count_on_page(page) == exp, f"'filter these jobs' link gave {count_on_page(page)}, expected {exp}"
    return f"Employer page lists {shown} jobs; its filter link opens the board filtered to that employer ({exp})"


def t_country_page(page, base, index):
    r = goto(page, base, "/countries/")
    assert r.status == 200
    first = page.locator(".index-grid a").first
    name = first.inner_text().split("\n")[0].strip()
    first.click()
    page.wait_for_load_state("domcontentloaded")
    assert name in page.locator("h1").inner_text()
    return f"Countries index opens '{name}' page correctly"


def t_no_hscroll(page, base, index):
    vp = page.viewport_size
    widths = (320, 360, 390, 412, 768)
    paths = ["/", f"/{index[0]['u']}/", "/companies/", "/guides/spot-fake-airline-job-offers/"]
    bad = []
    for w in widths:
        page.set_viewport_size({"width": w, "height": 800})
        for p in paths:
            goto(page, base, p)
            page.wait_for_timeout(200)
            sw = page.evaluate("document.documentElement.scrollWidth")
            # body has overflow-x: hidden so the user never scrolls sideways; allow
            # up to 4px for sub-pixel rounding differences across browsers at narrow widths
            if sw > w + 4:
                bad.append(f"{p}@{w}px={sw}")
    page.set_viewport_size(vp)
    # also with the longest filter choice made in the phone filter panel
    goto(page, base)
    wait_ready(page)
    if page.locator("[data-sheet-open]").is_visible():
        page.locator("[data-sheet-open]").click()
        page.wait_for_timeout(450)
        longest = page.evaluate("[...document.querySelectorAll('#f-role option')].sort((a,b)=>b.text.length-a.text.length)[0].value")
        page.select_option("#f-role", longest)
        page.wait_for_timeout(300)
        sw = page.evaluate("document.documentElement.scrollWidth")
        if sw > vp["width"] + 4:
            bad.append(f"filter panel with longest role = {sw}px")
        btn = page.locator(".sheet-apply").bounding_box()
        if not btn or btn["y"] + btn["height"] > vp["height"] + 1:
            bad.append("'Show jobs' button pushed off screen")
    assert not bad, "sideways scroll: " + ", ".join(bad)
    return f"No sideways scrolling on {len(paths)} pages at widths {', '.join(map(str, widths))}px"


def t_mobile_menu(page, base, index):
    goto(page, base)
    btn = page.locator("[data-menu]")
    if not btn.is_visible():
        raise Skip("menu button only on phones")
    btn.click()
    assert page.locator("#top-nav").is_visible()
    assert btn.get_attribute("aria-expanded") == "true"
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    assert page.locator("#top-nav").is_hidden()
    return "Menu opens with the button and closes with Escape"


def t_mobile_sheet(page, base, index):
    goto(page, base)
    wait_ready(page)
    btn = page.locator("[data-sheet-open]")
    if not btn.is_visible():
        raise Skip("filter sheet only on phones")
    btn.scroll_into_view_if_needed()
    btn.click()
    page.wait_for_timeout(450)
    assert "is-open" in page.locator("[data-sheet]").get_attribute("class")
    r = index[0]["r"]
    page.select_option("#f-role", r)
    exp = sum(j["r"] == r for j in index)
    label = page.locator("[data-apply-label]").inner_text()
    # strip thousand separators (e.g. "Show 2,528 jobs") before matching
    label_digits = re.sub(r"[,\s]", "", label)
    assert str(exp) in label_digits, f"button says {label!r}, expected {exp}"
    assert page.locator("[data-active-count]").inner_text().strip() == "1"
    page.locator("[data-scrim]").click(position={"x": 10, "y": 10})
    page.wait_for_timeout(450)
    assert "is-open" not in page.locator("[data-sheet]").get_attribute("class")
    return f"Filter panel opens, shows '{label}', badge shows 1, closes when tapping outside"


def t_apply_bar(page, base, index):
    goto(page, base, f"/{index[0]['u']}/")
    bar = page.locator(".apply-bar")
    if not bar.is_visible():
        raise Skip("sticky Apply bar is for phones")
    box = bar.bounding_box()
    vh = page.viewport_size["height"]
    assert box and box["y"] + box["height"] <= vh + 1 and box["y"] > vh - 120, "Apply bar not pinned to bottom"
    return "Apply button is pinned to the bottom of the phone screen"


def t_input_zoom(page, base, index):
    goto(page, base)
    fs = page.evaluate("parseFloat(getComputedStyle(document.querySelector('#q')).fontSize)")
    sel = page.evaluate("parseFloat(getComputedStyle(document.querySelector('#f-role')).fontSize)")
    assert fs >= 16 and sel >= 16, f"search {fs}px, select {sel}px"
    return f"Search box {fs:.0f}px and menus {sel:.0f}px: iPhones won't zoom in when typing"


def t_tap_targets(page, base, index):
    goto(page, base)
    small = page.evaluate("""() => [...document.querySelectorAll('button, .chip, select, .btn')]
        .filter(e => e.offsetParent).map(e => [e.className || e.tagName, e.getBoundingClientRect().height])
        .filter(([, h]) => h < 36)""")
    assert not small, f"small tap targets: {small[:5]}"
    return "Buttons, chips and menus are at least 36px tall"


def t_seo(page, base, index):
    r = page.request.get(base + "/sitemap.xml")
    assert r.status == 200
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text())
    assert locs and all(l.startswith("https://aerojobs.work/") for l in locs), "sitemap URLs wrong"
    rb = page.request.get(base + "/robots.txt").text()
    assert "Sitemap: https://aerojobs.work/sitemap.xml" in rb
    goto(page, base)
    canon = page.locator('link[rel="canonical"]').get_attribute("href")
    assert canon == "https://aerojobs.work/", f"canonical {canon}"
    missing = []
    for p in ("/", "/companies/", f"/{index[0]['u']}/", "/guides/"):
        goto(page, base, p)
        if not page.title() or not page.locator('meta[name="description"]').get_attribute("content"):
            missing.append(p)
    assert not missing, f"missing title/description: {missing}"
    return f"Sitemap has {len(locs)} pages on https://aerojobs.work; robots.txt points to it; canonical and descriptions present"


def t_manifest(page, base, index):
    for p in ("/site.webmanifest", "/static/icon-192.png", "/static/icon-512.png", "/static/apple-touch-icon.png",
              "/static/favicon.svg", "/static/hero-hangar.svg"):
        r = page.request.get(base + p)
        assert r.status == 200, f"{p}: {r.status}"
    return "Home-screen manifest, icons and banner image all load"


def t_a11y(page, base, index):
    goto(page, base)
    issues = page.evaluate("""() => {
      const out = [];
      if (!document.documentElement.lang) out.push('no lang');
      document.querySelectorAll('img').forEach(i => { if (!i.hasAttribute('alt')) out.push('img without alt'); });
      document.querySelectorAll('input, select').forEach(el => {
        if (el.type === 'hidden') return;
        const lab = el.labels && el.labels.length; const aria = el.getAttribute('aria-label');
        if (!lab && !aria) out.push('unlabelled ' + (el.id || el.name));
      });
      if (document.querySelectorAll('h1').length !== 1) out.push('h1 count ' + document.querySelectorAll('h1').length);
      return out; }""")
    assert not issues, "; ".join(issues[:6])
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement.textContent.trim()")
    assert "Skip to content" in focused, f"first Tab went to {focused!r}"
    return "Language set, images have alt text, every field has a label, one h1, 'Skip to content' is first on Tab"


def t_perf(page, base, index):
    t0 = time.time()
    goto(page, base)
    wait_ready(page)
    secs = time.time() - t0
    size = len(page.request.get(base + "/data/jobs-index.json").body())
    assert secs < 6, f"took {secs:.1f}s"
    return f"Home page with search ready in {secs:.1f}s; job list download {size/1024:.0f} KB"


def t_console_errors(page, base, index, errors):
    goto(page, base)
    wait_ready(page)
    goto(page, base, f"/{index[0]['u']}/")
    real = [e for e in errors if "googlesyndication" not in e and "fonts.g" not in e]
    assert not real, "; ".join(real[:3])
    return "No JavaScript errors on the home and job pages"


# ------------------------------------------------------------------ run
DESKTOP_CASES = [
    ("TC-NAV-01", "Navigation", "Functional", "Home page loads with headline and job count", "Open the home page", "HTTP 200, headline shown, job count equals live data", t_home_loads),
    ("TC-NAV-02", "Navigation", "Functional", "Header links and logo", "Click Employers, Countries, Guides, then the logo", "Each opens its page; logo returns home", t_header_links),
    ("TC-NAV-03", "Navigation", "Functional", "Role quick-filter chips", "Open each of the 8 role chips", "Each role page loads", t_role_chips),
    ("TC-NAV-04", "Navigation", "Functional", "Footer pages (About, Contact, Privacy, Terms)", "Open each footer page", "Pages load with the required content", t_footer_pages),
    ("TC-NAV-05", "Navigation", "Black box", "Unknown address shows a 404 page", "Open a made-up address", "HTTP 404 and a friendly page", t_404),
    ("TC-NAV-06", "Navigation", "End to end", "No broken internal links", "Follow every internal link from the home page", "No link returns an error", t_broken_links),
    ("TC-SRCH-01", "Search", "Functional", "Search by job title (case-insensitive)", "Type a common title word in capitals, click Search jobs", "Only matching jobs; count equals data", t_search_title),
    ("TC-SRCH-02", "Search", "Functional", "Search by employer name with Enter key", "Type an employer name, press Enter", "Only that employer's jobs", t_search_employer),
    ("TC-SRCH-03", "Search", "Black box", "No results and clearing the search", "Type nonsense, then clear the box", "'No jobs match' message; clearing restores all", t_search_none),
    ("TC-FLT-01", "Filters", "Functional", "Country and region filter", "Pick the busiest country, then its region", "Counts equal the data", t_filter_country),
    ("TC-FLT-02", "Filters", "Functional", "Job role filter", "Pick each role in turn", "Counts equal the data", t_filter_role),
    ("TC-FLT-03", "Filters", "Functional", "Work mode filter (single and combined)", "Tick On-site, Hybrid, Remote one at a time, then two together", "Counts equal the data", t_filter_mode),
    ("TC-FLT-04", "Filters", "Functional", "Posted date filter", "Pick 24h, 48h, week, month, older", "Counts equal the data", t_filter_posted),
    ("TC-FLT-05", "Filters", "Functional", "Employer type filter", "Pick each employer type", "Counts equal the data", t_filter_type),
    ("TC-FLT-06", "Filters", "End to end", "Combined filters, then Clear all", "Set country + role + mode, then Clear all", "Combined count correct; Clear all restores everything", t_filter_combined_and_clear),
    ("TC-FLT-08", "Filters", "Black box", "Filter counts update with other filters (owner's bug report)", "Tick Remote, read the counts next to each country, region and role; then pick a country and read the Remote count", "Every count reflects the other filters; choices with 0 jobs are greyed out", t_live_counts),
    ("TC-FLT-07", "Filters", "Black box", "Filters saved in a shareable link", "Open a link with filters, reload", "Filters applied from the link and kept on reload", t_url_state),
    ("TC-SORT-01", "Sorting", "Functional", "Newest first and Closing soonest", "Check default order, switch to Closing soonest", "Correct order both ways", t_sort),
    ("TC-PAGE-01", "Results list", "Functional", "Show more jobs", "Click Show more until all shown", "25 at a time; button hides at the end", t_show_more),
    ("TC-JOB-01", "Job page", "Functional", "Job details and Apply button", "Open a job", "Title, employer, dates; Apply opens employer site in new tab", t_job_page),
    ("TC-JOB-02", "Job page", "Functional", "Google for Jobs data on job pages", "Read the JobPosting data on 15 job pages", "Valid with title, date, employer, description, location", t_jsonld),
    ("TC-JOB-04", "Job page", "End to end", "Apply links reach each employer's site", "For one job per employer, follow the Apply link", "Employer page answers without error", t_apply_links_live),
    ("TC-JOB-03", "Job page", "End to end", "Breadcrumbs and similar jobs", "Click each breadcrumb; click a similar job", "All links work", t_breadcrumbs_similar),
    ("TC-LIST-01", "Listing pages", "End to end", "Employer page and its filter link", "Open an employer page, click 'Filter these jobs'", "Counts match; board opens filtered to that employer", t_company_page),
    ("TC-LIST-02", "Listing pages", "Functional", "Countries index", "Open Countries, click the first country", "Country page opens", t_country_page),
    ("TC-SEO-01", "SEO and AdSense readiness", "Functional", "Sitemap, robots.txt, canonical, descriptions", "Read sitemap.xml, robots.txt and page tags", "All present and on aerojobs.work", t_seo),
    ("TC-SEO-02", "SEO and AdSense readiness", "Functional", "Home-screen manifest and icons", "Request manifest and icons", "All load", t_manifest),
    ("TC-A11Y-01", "Accessibility", "Functional", "Basic accessibility", "Check labels, alt text, headings, keyboard skip link", "No issues", t_a11y),
    ("TC-PERF-01", "Performance", "Non-functional", "Home page speed", "Load home page until search is ready", "Under 6 seconds", t_perf),
]
MOBILE_CASES = [
    ("TC-MOB-01", "Phones", "Functional", "No sideways scrolling", "Open 4 page types at 320–768px wide", "Page never scrolls sideways", t_no_hscroll),
    ("TC-MOB-02", "Phones", "Functional", "Phone menu", "Tap the menu button, press Escape", "Menu opens and closes", t_mobile_menu),
    ("TC-MOB-03", "Phones", "End to end", "Filter panel on phones", "Open Filters, pick a role, tap outside", "Panel opens, shows live count, badge 1, closes", t_mobile_sheet),
    ("TC-MOB-04", "Phones", "Functional", "Sticky Apply button", "Open a job on a phone", "Apply button pinned to the bottom", t_apply_bar),
    ("TC-MOB-05", "Phones", "Functional", "No zoom when typing on iPhone", "Check text size of search box and menus", "At least 16px", t_input_zoom),
    ("TC-MOB-06", "Phones", "Functional", "Tap targets big enough", "Measure buttons and chips", "At least 36px tall", t_tap_targets),
    ("TC-FLT-02", "Filters", "Functional", "Job role filter", "Pick each role in turn (phone)", "Counts equal the data", t_filter_role),
    ("TC-FLT-08", "Filters", "Black box", "Filter counts update with other filters (owner's bug report)", "Same steps in the phone filter panel", "Counts reflect the other filters", t_live_counts),
    ("TC-SRCH-01", "Search", "Functional", "Search by job title (case-insensitive)", "Search on a phone", "Only matching jobs", t_search_title),
]


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--browsers", default="chromium")
    ap.add_argument("--out", default="qa-results")
    ap.add_argument("--quick", action="store_true", help="desktop core cases only")
    args = ap.parse_args()
    OUT = Path(args.out)
    OUT.mkdir(parents=True, exist_ok=True)
    base = args.base.rstrip("/")
    with sync_playwright() as p:
        for bname in args.browsers.split(","):
            btype = getattr(p, bname)
            browser = btype.launch()
            print(f"\n=== {bname} ===", flush=True)
            # desktop
            ctx = browser.new_context(viewport={"width": 1366, "height": 900})
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            index = page.request.get(base + "/data/jobs-index.json").json()["jobs"]
            if not index:
                print("No jobs on the site yet; stopping.")
                return
            info = (bname, "Desktop 1366px", page)
            for c in DESKTOP_CASES:
                run_case(info, *c, base, index)
            run_case(info, "TC-JS-01", "Reliability", "Non-functional", "No JavaScript errors", "Open home and a job page, watch the console",
                     "No errors", t_console_errors, base, index, errors)
            (OUT / "screens").mkdir(parents=True, exist_ok=True)
            page.set_viewport_size({"width": 1366, "height": 900})
            goto(page, base)
            wait_ready(page)
            page.screenshot(path=str(OUT / "screens" / f"home-{bname}-desktop.png"))
            ctx.close()
            # phone
            if bname == "chromium":
                dev, kw = "Pixel 7 (Android)", dict(p.devices["Pixel 7"])
            elif bname == "webkit":
                dev, kw = "iPhone 13 (iOS Safari engine)", dict(p.devices["iPhone 13"])
            else:
                dev, kw = "Phone 390px (Firefox)", {"viewport": {"width": 390, "height": 844}}
            ctx = browser.new_context(**kw)
            page = ctx.new_page()
            info = (bname, dev, page)
            for c in MOBILE_CASES:
                run_case(info, *c, base, index)
            goto(page, base)
            wait_ready(page)
            page.screenshot(path=str(OUT / "screens" / f"home-{bname}-phone.png"))
            ctx.close()
            browser.close()
    (OUT / "results.json").write_text(json.dumps({"base": base, "run": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                  "results": RESULTS}, indent=1, ensure_ascii=False))
    s = {k: sum(r["status"] == k for r in RESULTS) for k in ("Pass", "Fail", "Skip")}
    print(f"\nTotal {len(RESULTS)}: {s}")


if __name__ == "__main__":
    main()
