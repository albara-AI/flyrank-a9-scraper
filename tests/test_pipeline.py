"""End-to-end checkpoints (Stages 2-5) against the offline replica."""
import json

from config import Settings
from fetcher import PoliteFetcher
from main import BROKEN_URL, main
from replica import replica_session

ATTIC_PATH = "/catalogue/a-light-in-the-attic_1000/index.html"


def run_cli(tmp_path, *args, **faults):
    session, adapter = replica_session(**faults)
    settings = Settings(cache_dir=tmp_path / "cache", output_dir=tmp_path / "out",
                        delay_seconds=0.0, retry_wait_seconds=0.0)
    code = main(list(args), session=session, settings=settings)
    out = tmp_path / "out"
    read = lambda name: json.loads((out / name).read_text(encoding="utf-8"))
    return code, adapter, read


def test_full_run_then_rerun_is_identical_and_cached(tmp_path):
    code, adapter, read = run_cli(tmp_path)
    first = (tmp_path / "out" / "books.json").read_bytes()
    report = read("run-report.json")
    assert code == 0
    assert (report["catalogue_pages"], report["discovered_urls"], report["unique_urls"]) == (3, 60, 60)
    assert (report["detail_pages"], report["valid_records"], report["failed_pages"]) == (60, 60, 0)
    assert report["network_requests"] == 63 and len(adapter.log) == 63
    assert "/catalogue/page-4.html" not in {r["path"] for r in adapter.log}

    code, adapter, read = run_cli(tmp_path)
    assert code == 0 and len(adapter.log) == 0 and read("run-report.json")["cache_hits"] == 63
    assert (tmp_path / "out" / "books.json").read_bytes() == first   # idempotent


def test_books_json_contract(tmp_path):
    _, _, read = run_cli(tmp_path)
    books = read("books.json")
    assert len(books) == 60 == len({b["product_url"] for b in books})
    assert all(isinstance(b["price_gbp"], float) for b in books)
    assert all(b["product_url"].startswith("https://") for b in books)
    assert read("errors.json") == []


def test_one_broken_url_is_skipped_and_reported(tmp_path):
    code, _, read = run_cli(tmp_path, "--inject-broken-url")
    report = read("run-report.json")
    assert code == 2 and report["failed_pages"] == 1
    assert report["failures"] == [{"url": BROKEN_URL, "stage": "detail", "reason": "HTTP 404"}]
    assert len(read("books.json")) == 60


def test_flaky_page_is_retried_and_still_lands(tmp_path):
    code, _, read = run_cli(tmp_path, fail_once={ATTIC_PATH})
    report = read("run-report.json")
    assert code == 0 and report["retries"] == 1 and report["valid_records"] == 60


def test_dead_page_does_not_kill_the_run(tmp_path):
    code, _, read = run_cli(tmp_path, always_fail={ATTIC_PATH})
    report = read("run-report.json")
    assert code == 2 and report["failed_pages"] == 1 and report["valid_records"] == 59
    assert report["failures"][0]["reason"] == "HTTP 500"


def test_broken_catalogue_page_stops_discovery_cleanly(tmp_path):
    code, _, read = run_cli(tmp_path, always_fail={"/catalogue/page-2.html"})
    report = read("run-report.json")
    assert code == 2 and report["catalogue_pages"] == 1 and report["valid_records"] == 20
    assert report["failures"][0]["stage"] == "catalogue"
