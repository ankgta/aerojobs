"""Security and penetration checks for the live AeroJobs website.

    python qa/security_tests.py --base https://aerojobs.work --out qa-results

Safe, low-volume checks only: it never floods the site or tries to break Cloudflare.
Browser-based injection tests use Playwright. Results go to security.json.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import subprocess
import urllib.parse
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

RESULTS: list[dict] = []
UA = {"User-Agent": "AeroJobs-QA/1.0 (owner's own security check)"}


def rec(tc, area, title, attack, expected, status, actual, severity="-"):
    RESULTS.append({"id": tc, "area": area, "title": title, "attack": attack, "expected": expected,
                    "status": status, "actual": actual, "severity": severity})
    print(f"  {'✓' if status == 'Pass' else ('✗' if status == 'Fail' else '!')} {tc} {title}: {actual[:150]}", flush=True)


def check(tc, area, title, attack, expected, fn, severity_if_fail="Medium"):
    try:
        ok, actual = fn()
        rec(tc, area, title, attack, expected, "Pass" if ok else "Fail", actual, "-" if ok else severity_if_fail)
    except Exception as e:
        rec(tc, area, title, attack, expected, "Fail", f"{type(e).__name__}: {str(e)[:200]}", severity_if_fail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", default="qa-results")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    host = urllib.parse.urlsplit(base).netloc
    s = requests.Session()
    s.headers.update(UA)
    home = s.get(base + "/", timeout=30)
    h = {k.lower(): v for k, v in home.headers.items()}

    # ---- transport
    def https_redirect():
        r = s.get(f"http://{host}/", allow_redirects=False, timeout=30)
        loc = r.headers.get("location", "")
        return r.status_code in (301, 302, 307, 308) and loc.startswith("https://"), f"HTTP {r.status_code} -> {loc or 'no redirect'}"
    check("SEC-01", "Transport", "Plain http redirects to https", "Request http://", "Redirect to https", https_redirect, "High")

    def hsts():
        v = h.get("strict-transport-security", "")
        return "max-age=" in v and int(v.split("max-age=")[1].split(";")[0]) >= 15552000, v or "missing"
    check("SEC-02", "Transport", "HSTS header", "Read response headers", "max-age of at least 6 months", hsts)

    def tls_old():
        out = []
        for name, ver in (("TLS 1.0", ssl.TLSVersion.TLSv1), ("TLS 1.1", ssl.TLSVersion.TLSv1_1)):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.minimum_version = ver
                ctx.maximum_version = ver
                ctx.set_ciphers("ALL:@SECLEVEL=0")
                with socket.create_connection((host, 443), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host):
                        out.append(f"{name} ACCEPTED")
            except Exception:
                out.append(f"{name} refused")
        return all("refused" in x for x in out), ", ".join(out)
    check("SEC-03", "Transport", "Old TLS versions refused", "Connect with TLS 1.0 and 1.1", "Both refused", tls_old, "Low")

    def cert():
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                c = ss.getpeercert()
                return True, f"valid, issued to {dict(x[0] for x in c['subject']).get('commonName')}, expires {c['notAfter']}, {ss.version()}"
    check("SEC-04", "Transport", "Valid TLS certificate", "Verify the certificate chain", "Trusted and in date", cert, "High")

    # ---- headers
    for tc, name, want, sev in (("SEC-05", "content-security-policy", "frame-ancestors", "Medium"),
                                ("SEC-06", "x-frame-options", "SAMEORIGIN", "Medium"),
                                ("SEC-07", "x-content-type-options", "nosniff", "Low"),
                                ("SEC-08", "referrer-policy", "strict-origin", "Low"),
                                ("SEC-09", "permissions-policy", "camera=()", "Low")):
        check(tc, "Security headers", f"{name} header", "Read response headers", f"Contains {want!r}",
              lambda name=name, want=want: (want.lower() in h.get(name, "").lower(), h.get(name, "missing")), sev)

    def disclosure():
        leaks = {k: h[k] for k in ("x-powered-by", "x-aspnet-version", "x-generator") if k in h}
        return not leaks, f"Server: {h.get('server', '-')}; " + (f"leaks {leaks}" if leaks else "no technology leaks")
    check("SEC-10", "Information disclosure", "No software version leaks in headers", "Read response headers", "No X-Powered-By and similar", disclosure, "Low")

    def cookies():
        return not home.cookies, f"{len(home.cookies)} cookies set by the site" if home.cookies else "No cookies set by the site itself"
    check("SEC-11", "Session", "No cookies or logins to steal", "Check Set-Cookie", "None set", cookies, "Low")

    # ---- exposed files
    def exposed():
        paths = ["/.git/config", "/.git/HEAD", "/.env", "/config/site.yaml", "/config/employers.yaml", "/fetcher/run.py",
                 "/requirements.txt", "/.github/workflows/update.yml", "/data/jobs.json", "/data/role_cache.json",
                 "/README.md", "/SETUP-GUIDE.md", "/tests/test_site.py", "/wrangler.toml", "/_headers"]
        found = []
        for p in paths:
            r = s.get(base + p, timeout=20, allow_redirects=True)
            body = r.text[:300].lower()
            # Pages serves the 404 page for unknown files; anything else that looks like the real file is a leak
            if r.status_code == 200 and "left the gate" not in body:
                found.append(p)
        return not found, f"{len(paths)} private paths tried; exposed: {found or 'none'}"
    check("SEC-12", "Exposed files", "Private files not downloadable", "Request .git, .env, config, code and raw data files",
          "All return the 404 page", exposed, "High")

    def listing():
        hits = []
        for p in ("/static/", "/jobs/", "/data/", "/companies/../"):
            r = s.get(base + p, timeout=20)
            if r.status_code == 200 and ("index of" in r.text.lower() or "<pre>" in r.text.lower()):
                hits.append(p)
        return not hits, f"directory listings: {hits or 'none'}"
    check("SEC-13", "Exposed files", "No directory listings", "Request folder addresses", "No file lists shown", listing, "Medium")

    def traversal():
        bad = []
        for p in ("/..%2f..%2f..%2fetc%2fpasswd", "/%2e%2e/%2e%2e/etc/passwd", "/static/..%2f..%2fconfig%2fsite.yaml"):
            r = s.get(base + p, timeout=20)
            if "root:" in r.text or "site_name" in r.text:
                bad.append(p)
        return not bad, "path traversal attempts all blocked" if not bad else f"LEAK via {bad}"
    check("SEC-14", "Injection", "Path traversal", "Encoded ../ sequences", "No system or config files returned", traversal, "High")

    # ---- methods and odd requests
    def methods():
        out = []
        for m in ("POST", "PUT", "DELETE", "PATCH"):
            r = s.request(m, base + "/", timeout=20, data="x=1")
            out.append(f"{m} {r.status_code}")
        after = s.get(base + "/", timeout=20)
        unchanged = after.status_code == 200 and "Every aviation job" in after.text
        return unchanged and all(not x.endswith(("201", "204")) for x in out), ", ".join(out) + "; site unchanged afterwards" if unchanged else "SITE CHANGED"
    check("SEC-15", "HTTP methods", "Write methods do nothing", "Send POST, PUT, DELETE, PATCH", "Rejected or ignored; site unchanged", methods, "High")

    def long_query():
        r = s.get(base + "/?q=" + "A" * 6000, timeout=30)
        return r.status_code < 500, f"HTTP {r.status_code}"
    check("SEC-16", "Robustness", "Very long query string", "6,000-character search parameter", "No server error", long_query, "Low")

    def open_redirect():
        bad = []
        for p in ("/?next=https://evil.example", "/?redirect=https://evil.example", "//evil.example/", "/%2F%2Fevil.example"):
            r = s.get(base + p, allow_redirects=False, timeout=20)
            if r.status_code in (301, 302, 307, 308) and "evil.example" in r.headers.get("location", ""):
                bad.append(p)
        return not bad, "no redirects to outside sites" if not bad else f"redirects via {bad}"
    check("SEC-17", "Injection", "Open redirect", "Redirect-style parameters to an outside site", "Never redirected", open_redirect, "Medium")

    def mixed():
        import re
        insecure = [u for u in re.findall(r'(?:src|href)="(http://[^"]+)"', home.text)]
        return not insecure, f"insecure resources: {insecure or 'none'}"
    check("SEC-18", "Transport", "No mixed content", "Scan home page for http:// resources", "All resources https", mixed, "Low")

    # ---- browser-based injection
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        fired = []
        pg.on("dialog", lambda d: (fired.append(d.message), d.dismiss()))
        payloads = ['<script>alert("xss1")</script>', '"><img src=x onerror=alert("xss2")>',
                    "<svg onload=alert('xss3')>", "javascript:alert('xss4')", "' OR '1'='1' --", "\" ; DROP TABLE jobs; --"]

        def reflected():
            for pl in payloads:
                q = urllib.parse.quote(pl)
                pg.goto(f"{base}/?q={q}&country={q}&role={q}&mode={q}&sort={q}&company={q}#jobs")
                pg.wait_for_timeout(1200)
            injected = pg.evaluate("document.querySelectorAll('img[src=x], svg[onload], script:not([src]):not([type])').length")
            return not fired and injected <= 3, f"{len(payloads)} payloads in 6 URL parameters; alerts fired: {len(fired)}; page still works: {pg.locator('h1').count() == 1}"
        check("SEC-19", "Cross-site scripting", "Reflected XSS through URL parameters",
              "Script and HTML payloads in q, country, role, mode, sort, company", "No script runs; text shown as text", reflected, "High")

        def typed():
            pg.goto(base + "/")
            pg.wait_for_timeout(1500)
            for pl in payloads:
                pg.fill("#q", pl)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(300)
            val = pg.input_value("#q")
            return not fired, f"alerts fired: {len(fired)}; the box keeps the text as typed ({val[:30]!r})"
        check("SEC-20", "Cross-site scripting", "XSS typed into the search box", "Type the payloads and press Enter",
              "No script runs", typed, "High")

        def sql():
            pg.goto(base + "/?q=" + urllib.parse.quote("' OR 1=1 --"))
            pg.wait_for_timeout(1500)
            txt = pg.locator("[data-count]").inner_text()
            return "error" not in pg.content().lower()[:2000] and not fired, f"no database to inject into; page shows '{txt}'"
        check("SEC-21", "Injection", "SQL injection", "' OR 1=1 -- in the search", "No error, no data leak", sql, "High")

        def framing():
            pg.set_content(f'<iframe id=f src="{base}/" width=400 height=300></iframe>')
            pg.wait_for_timeout(3000)
            fr = pg.frame_locator("#f")
            try:
                loaded = fr.locator("h1").count() > 0
            except Exception:
                loaded = False
            return not loaded, "another site cannot show AeroJobs inside a frame" if not loaded else "PAGE LOADED INSIDE A FOREIGN FRAME"
        check("SEC-22", "Clickjacking", "Site cannot be framed by other sites", "Embed the site in an iframe on another page",
              "Browser refuses to show it", framing, "Medium")
        b.close()

    # ---- what we deliberately did not do
    rec("SEC-23", "Denial of service", "Flood / DDoS resistance", "Not attempted (would attack Cloudflare's network)",
        "Handled by Cloudflare's free DDoS protection", "Not tested", "Not tested on purpose; static files on Cloudflare's network", "-")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "security.json").write_text(json.dumps({"base": base, "results": RESULTS}, indent=1, ensure_ascii=False))
    print(f"\n{sum(r['status'] == 'Pass' for r in RESULTS)} passed, {sum(r['status'] == 'Fail' for r in RESULTS)} failed")


if __name__ == "__main__":
    main()
