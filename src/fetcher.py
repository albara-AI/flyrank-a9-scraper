"""Stage 1: polite fetching with a disk cache.

Rules: honest user-agent, timeout on every request, only HTTP 200 counts,
a delay between real requests, and one retry for timeouts / 5xx only.
A cached page never leaves your computer, so it needs no delay.
"""
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

from config import Settings


class FetchError(Exception):
    """A page that did not arrive as HTTP 200. `reason` goes into the run report."""

    def __init__(self, url: str, reason: str, status: int | None = None):
        super().__init__(f"{reason}: {url}")
        self.url, self.reason, self.status = url, reason, status


@dataclass(frozen=True)
class Page:
    url: str
    html: str
    fetched_at: str     # when the site really sent it (kept in the cache, so reruns don't lie)
    from_cache: bool
    size_bytes: int


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_name(url: str) -> str:
    """catalogue/page-1.html -> catalogue-page-1.html (one flat, readable folder)."""
    path = urlsplit(url).path.strip("/") or "index.html"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", path)


class PoliteFetcher:
    def __init__(self, settings: Settings, session=None, sleep=time.sleep, clock=time.monotonic, log=print):
        self.s = settings
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = settings.user_agent
        self._sleep, self._clock, self._log = sleep, clock, log
        self._last_request = None
        self.stats = {"network_requests": 0, "pages_fetched": 0, "cache_hits": 0, "retries": 0}

    def get(self, url: str) -> Page:
        html_path = self.s.cache_dir / cache_name(url)
        meta_path = html_path.parent / (html_path.name + ".meta.json")
        if html_path.exists() and meta_path.exists():
            raw = html_path.read_bytes()
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.stats["cache_hits"] += 1
            self._log(f"CACHE HIT  {html_path.name}  {len(raw):,} bytes")
            return Page(url, raw.decode("utf-8", errors="replace"), meta["fetched_at"], True, len(raw))

        raw, fetched_at = self._download(url)
        self.s.cache_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_bytes(raw)
        meta = {"url": url, "status": 200, "fetched_at": fetched_at}
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        self.stats["pages_fetched"] += 1
        self._log(f"FETCH      {html_path.name}  {len(raw):,} bytes")
        # Decode the bytes ourselves: the server sends no charset, so resp.text would show "Â£51.77".
        return Page(url, raw.decode("utf-8", errors="replace"), fetched_at, False, len(raw))

    def probe(self, url: str) -> requests.Response:
        """One polite request that is never cached (used for robots.txt)."""
        self._wait_turn()
        return self.session.get(url, timeout=self.s.timeout_seconds)

    def _download(self, url: str) -> tuple[bytes, str]:
        for attempt in (1, 2):
            self._wait_turn()
            try:
                resp = self.session.get(url, timeout=self.s.timeout_seconds)
            except (requests.Timeout, requests.ConnectionError) as exc:
                reason = f"network error ({type(exc).__name__})"
                status = None
            else:
                if resp.status_code == 200:
                    return resp.content, utc_now()
                reason, status = f"HTTP {resp.status_code}", resp.status_code
                if not 500 <= resp.status_code < 600:
                    raise FetchError(url, reason, status)  # 404/403: asking again won't help
            if attempt == 1:
                self.stats["retries"] += 1
                self._log(f"RETRY      {cache_name(url)}  after {reason}")
                self._sleep(self.s.retry_wait_seconds)
        raise FetchError(url, reason, status)

    def _wait_turn(self) -> None:
        if self._last_request is not None:
            remaining = self.s.delay_seconds - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request = self._clock()
        self.stats["network_requests"] += 1
