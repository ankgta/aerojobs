from fetcher.discover_aero import aero_sites_on_page, careers_link, read_directory, subcategory_urls


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


def test_subcategory_urls_finds_two_segment_links_only():
    # Real link shapes seen on information.aero/directory and its category pages.
    html = """
    <a href="https://information.aero/category/registrant_group/aerial_works">Aerial works</a>
    <a href="https://information.aero/category/registrant_group/airlines_and_commercial_operators">Airlines</a>
    <a href="https://information.aero/category/registrant_group/aerialworks/aerial_photography">Photo</a>
    <a href="https://information.aero/category/registrant_group/airlinesandcommercialoperators/cargo_carriers">Cargo</a>
    """
    subs = subcategory_urls(html)
    assert subs == [
        "https://information.aero/category/registrant_group/aerialworks/aerial_photography",
        "https://information.aero/category/registrant_group/airlinesandcommercialoperators/cargo_carriers",
    ]


class _FakeAeroClient:
    """A fake PoliteClient standing in for the real one, keyed by URL."""
    def __init__(self, pages: dict):
        self.pages = pages
        self.calls: list[str] = []

    def get_text(self, url: str) -> str:
        self.calls.append(url)
        return self.pages.get(url, "")


def test_read_directory_visits_only_relevant_subcategories_from_the_index_page():
    # A regression test for a real bug: an earlier version of read_directory() only
    # looked for subcategory links that happened not to be on the index page in the
    # expected shape, and silently returned 0 results. The index page actually links
    # directly to subcategory pages (confirmed by inspecting information.aero live),
    # so read_directory() must find and use those links with no extra page fetch.
    index_html = """
    <a href="https://information.aero/category/registrant_group/aerialworks/aerial_photography">Photo</a>
    <a href="https://information.aero/category/registrant_group/airlinesandcommercialoperators/cargo_carriers">Cargo</a>
    <a href="https://information.aero/category/registrant_group/airlinesandcommercialoperators/charter_carriers">Charter</a>
    <a href="https://information.aero/category/registrant_group/aerospace/distribution">Distribution</a>
    """
    pages = {
        "https://information.aero/directory": index_html,
        "https://information.aero/category/registrant_group/airlinesandcommercialoperators/cargo_carriers":
            '<a href="https://www.testcargo.aero">Test Cargo Co</a><a href="https://charter.aero">Charter Air</a>',
        "https://information.aero/category/registrant_group/airlinesandcommercialoperators/charter_carriers":
            '<a href="https://charter.aero">Charter Air dup</a>',
        "https://information.aero/category/registrant_group/aerospace/distribution":
            '<a href="https://partsco.aero">Parts Co</a>',
    }
    client = _FakeAeroClient(pages)
    sites = read_directory(client)
    assert sorted(s["domain"] for s in sites) == ["charter.aero", "partsco.aero", "testcargo.aero"]
    # "aerial_works" is not in RELEVANT_CATEGORIES, so its subcategory page is never fetched.
    assert not any("aerialworks" in u for u in client.calls)
    # Only one fetch per unique page (the index, plus the three relevant subcategory pages).
    assert client.calls.count("https://information.aero/directory") == 1


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
