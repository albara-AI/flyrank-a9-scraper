"""fetch -> extract -> normalize -> validate -> store -> report, one stage per function."""
import time

from clean import validate
from config import Settings
from fetcher import PoliteFetcher, utc_now
from parse import parse_book, parse_catalogue
from store import upsert_books, write_json


def _reason(exc: Exception) -> str:
    """FetchError/ParseError carry a clean reason; anything unexpected keeps its type name."""
    return getattr(exc, "reason", None) or f"{type(exc).__name__}: {exc}"


def discover(settings: Settings, fetcher: PoliteFetcher, failures: list, log=print) -> dict:
    """Stage 2: follow the site's own "next" link for N pages; return {book_url: source_page}."""
    sources, discovered, pages, page_url = {}, 0, 0, settings.start_url
    while page_url and pages < settings.max_catalogue_pages:
        try:
            page = fetcher.get(page_url)
            links, next_url = parse_catalogue(page.html, page.url)
        except Exception as exc:  # one bad page must not kill the run
            failures.append({"url": page_url, "stage": "catalogue", "reason": _reason(exc)})
            log(f"SKIP       {page_url}  ({_reason(exc)}); cannot follow 'next' past it")
            break
        pages += 1
        discovered += len(links)
        for link in links:
            sources.setdefault(link, page.url)  # first page that listed it = provenance; repeats dropped
        page_url = next_url
    log(f"catalogue_pages={pages} discovered={discovered} unique_urls={len(sources)}")
    return {"sources": sources, "catalogue_pages": pages, "discovered": discovered}


def extract(sources: dict, fetcher: PoliteFetcher, failures: list, log=print) -> list[dict]:
    """Stage 3: visit every book page politely; one bad page is logged and skipped."""
    records = []
    for url, source_page in sources.items():
        try:
            page = fetcher.get(url)
            records.append(parse_book(page.html, url, source_page, page.fetched_at))
        except Exception as exc:  # one bad page must not kill the run
            failures.append({"url": url, "stage": "detail", "reason": _reason(exc)})
            log(f"SKIP       {url}  ({_reason(exc)})")
    log(f"detail_pages={len(records)}")
    return records


def clean_and_store(settings: Settings, raw: list[dict], log=print) -> dict:
    """Stage 4: normalize + validate every record, store only the good ones."""
    books, errors = validate(raw)
    total = upsert_books(settings.output_dir / "books.json", books)
    write_json(settings.output_dir / "errors.json", errors)
    log(f"valid_records={len(books)} invalid_records={len(errors)} books_json_total={total}")
    return {"valid": len(books), "invalid": len(errors), "total": total}


def run(settings: Settings, fetcher: PoliteFetcher, extra_urls=(), log=print) -> dict:
    """The whole pipeline. Always ends by writing output/run-report.json."""
    started_at, t0, failures = utc_now(), time.monotonic(), []
    found = discover(settings, fetcher, failures, log)
    sources = dict(found["sources"])
    for url in extra_urls:  # Stage 5 proof: a made-up URL, broken on our side only
        sources.setdefault(url, settings.start_url)
    raw = extract(sources, fetcher, failures, log)
    stored = clean_and_store(settings, raw, log)
    report = {
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(time.monotonic() - t0, 2),
        "target": settings.start_url,
        "catalogue_pages": found["catalogue_pages"],
        "discovered_urls": found["discovered"],
        "unique_urls": len(found["sources"]),
        "injected_urls": len(extra_urls),
        **fetcher.stats,  # network_requests, pages_fetched, cache_hits, retries
        "detail_pages": len(raw),
        "valid_records": stored["valid"],
        "invalid_records": stored["invalid"],
        "failed_pages": len(failures),
        "books_json_total": stored["total"],
        "failures": failures,
    }
    write_json(settings.output_dir / "run-report.json", report)
    return report
