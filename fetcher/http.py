"""A polite web client: obeys robots.txt, pauses between requests, retries gently."""
from __future__ import annotations

import time
import urllib.parse
import urllib.robotparser

import requests

USER_AGENT = "AviationJobsPortalBot/1.0 (job listing aggregator; links back to employer sites)"


class RobotsBlocked(Exception):
    """The website's robots.txt does not allow us to read this address."""


class FetchError(Exception):
    pass


class PoliteClient:
    def __init__(self, user_agent: str = USER_AGENT, delay: float = 1.5, timeout: float = 30):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Language": "en",
        })
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request: dict[str, float] = {}
        self.request_count = 0

    # ---- robots.txt (RFC 9309: 4xx = allowed, 5xx / unreachable = not allowed) ----
    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is not None:
            return rp
        rp = urllib.robotparser.RobotFileParser()
        try:
            self._wait(parts.netloc)
            r = self.session.get(base + "/robots.txt", timeout=self.timeout)
            self.request_count += 1
            if 400 <= r.status_code < 500:
                rp.parse([])
            elif r.status_code >= 500:
                rp.disallow_all = True
            else:
                rp.parse(r.text.splitlines())
        except requests.RequestException:
            rp.disallow_all = True
        self._robots[base] = rp
        return rp

    def check_allowed(self, url: str) -> None:
        if not self._robots_for(url).can_fetch(self.user_agent, url):
            raise RobotsBlocked(f"robots.txt does not allow {url}")

    # ---- pacing ----
    def _wait(self, host: str) -> None:
        last = self._last_request.get(host)
        if last is not None:
            gap = time.monotonic() - last
            if gap < self.delay:
                time.sleep(self.delay - gap)
        self._last_request[host] = time.monotonic()

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.check_allowed(url)
        host = urllib.parse.urlsplit(url).netloc
        last_error = None
        for attempt in range(3):
            self._wait(host)
            try:
                r = self.session.request(method, url, timeout=self.timeout, **kwargs)
                self.request_count += 1
            except requests.RequestException as e:
                last_error = e
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last_error = FetchError(f"HTTP {r.status_code} from {url}")
                retry_after = r.headers.get("Retry-After", "")
                time.sleep(int(retry_after) if retry_after.isdigit() and int(retry_after) < 120 else 10 * (attempt + 1))
                continue
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code} from {url}")
            return r
        raise FetchError(f"Gave up on {url}: {last_error}")

    def get_json(self, url: str, params: dict | None = None, **kwargs):
        return self.request("GET", url, params=params, headers={"Accept": "application/json"}, **kwargs).json()

    def post_json(self, url: str, payload: dict):
        return self.request("POST", url, json=payload,
                            headers={"Accept": "application/json", "Content-Type": "application/json"}).json()

    def get_text(self, url: str) -> str:
        return self.request("GET", url, headers={"Accept": "text/html,application/xhtml+xml"}).text
