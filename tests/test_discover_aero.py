from fetcher.discover_aero import aero_sites_on_page, careers_link


def test_listing_page_finds_external_aero_sites_only():
    html = """
    <a href="/taxonomy/term/12">Airlines</a>
    <a href="https://information.aero/kesteven_aero">Kesteven aero</a>
    <a href="http://www.tdt.aero">TD Team</a>
    <a href="http://www.tdt.aero/">http://www.tdt.aero</a>
    <a href="https://ndb.aero/en">Technomarine JSC</a>
    <a href="https://example.com">Not aero</a>
    <a href="javascript:void(0)">x</a>
    """
    sites = aero_sites_on_page(html)
    assert [s["domain"] for s in sites] == ["tdt.aero", "ndb.aero"]
    assert sites[0]["name"] == "TD Team" and sites[0]["url"] == "https://www.tdt.aero/"


def test_careers_link_prefers_clear_matches():
    html = """
    <a href="/about">About us</a>
    <a href="/news/jobs-report-2026">Industry news</a>
    <a href="/careers">Careers</a>
    <a href="mailto:jobs@x.aero">Email</a>
    """
    assert careers_link("https://www.x.aero/", html) == "https://www.x.aero/careers"
    assert careers_link("https://www.x.aero/", '<a href="/contact">Contact</a>') is None
    assert careers_link("https://www.x.aero/", '<a href="/join">Join our team</a>') == "https://www.x.aero/join"
