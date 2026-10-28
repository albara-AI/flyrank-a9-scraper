"""Politeness rules, proven against the replica transport (no real network)."""
from dataclasses import replace

import pytest

from config import Settings
from fetcher import FetchError, PoliteFetcher
from replica import replica_session

PAGE_1 = "https://books.toscrape.com/catalogue/page-1.html"
ATTIC = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


class FakeTime:
    """sleep() advances the clock, so delays are checked without waiting."""
    def __init__(self):
        self.now, self.sleeps = 100.0, []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))
        self.now += seconds


def make(tmp_path, **faults):
    session, adapter = replica_session(**faults)
    t = FakeTime()
    settings = Settings(cache_dir=tmp_path / "cache", output_dir=tmp_path / "out")
    fetcher = PoliteFetcher(settings, session=session, sleep=t.sleep, clock=t.clock, log=lambda *_: None)
    return fetcher, adapter, t


def test_identifies_itself_and_always_sets_a_timeout(tmp_path):
    fetcher, adapter, _ = make(tmp_path)
    fetcher.get(PAGE_1)
    assert adapter.log[0]["user_agent"].startswith("FlyRankInternshipA9/1.0 (+https://")
    assert adapter.log[0]["timeout"] == Settings().timeout_seconds


def test_second_get_is_a_cache_hit_with_the_original_fetched_at(tmp_path):
    fetcher, adapter, _ = make(tmp_path)
    first = fetcher.get(PAGE_1)
    second = fetcher.get(PAGE_1)
    assert (first.from_cache, second.from_cache) == (False, True)
    assert second.fetched_at == first.fetched_at and second.html == first.html
    assert len(adapter.log) == 1 and (tmp_path / "cache" / "catalogue-page-1.html").exists()


def test_pound_sign_survives_the_missing_charset(tmp_path):
    fetcher, _, _ = make(tmp_path)
    assert "£51.77" in fetcher.get(PAGE_1).html


def test_waits_between_real_requests_but_not_for_cache(tmp_path):
    fetcher, _, t = make(tmp_path)
    fetcher.get(PAGE_1)
    fetcher.get(ATTIC)
    fetcher.get(PAGE_1)  # cache hit: no delay needed
    assert t.sleeps == [Settings().delay_seconds]
    assert Settings().delay_seconds >= 0.5


def test_404_is_not_retried(tmp_path):
    fetcher, adapter, _ = make(tmp_path)
    with pytest.raises(FetchError) as err:
        fetcher.get("https://books.toscrape.com/catalogue/nope_0/index.html")
    assert err.value.status == 404 and len(adapter.log) == 1 and fetcher.stats["retries"] == 0


def test_5xx_is_retried_once_then_succeeds(tmp_path):
    fetcher, adapter, t = make(tmp_path, fail_once={"/catalogue/page-1.html"})
    page = fetcher.get(PAGE_1)
    assert page.size_bytes > 0 and len(adapter.log) == 2 and fetcher.stats["retries"] == 1
    assert Settings().retry_wait_seconds in t.sleeps


def test_timeout_is_retried_once_then_succeeds(tmp_path):
    fetcher, adapter, _ = make(tmp_path, timeout_once={"/catalogue/page-1.html"})
    assert fetcher.get(PAGE_1).size_bytes > 0 and len(adapter.log) == 2


def test_persistent_5xx_gives_up_after_one_retry_and_caches_nothing(tmp_path):
    fetcher, adapter, _ = make(tmp_path, always_fail={"/catalogue/page-1.html"})
    with pytest.raises(FetchError) as err:
        fetcher.get(PAGE_1)
    assert err.value.status == 500 and len(adapter.log) == 2
    assert not (tmp_path / "cache" / "catalogue-page-1.html").exists()
