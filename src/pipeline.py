"""fetch -> extract -> normalize -> validate -> store -> report, one stage per function."""
from config import Settings
from fetcher import FetchError, PoliteFetcher
from parse import ParseError, parse_book, parse_catalogue


def discover(settings: Settings, fetcher: PoliteFetcher, failures: list, log=print) -> dict:
    """Stage 2: follow the site's own "next" link for N pages; return {book_url: source_page}."""
    sources, discovered, pages, page_url = {}, 0, 0, settings.start_url
    while page_url and pages < settings.max_catalogue_pages:
        try:
            page = fetcher.get(page_url)
            links, next_url = parse_catalogue(page.html, page.url)
        except (FetchError, ParseError) as exc:
            failures.append({"url": page_url, "stage": "catalogue", "reason": exc.reason})
            log(f"SKIP       {page_url}  ({exc.reason}); cannot follow 'next' past it")
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
        except (FetchError, ParseError) as exc:
            failures.append({"url": url, "stage": "detail", "reason": exc.reason})
            log(f"SKIP       {url}  ({exc.reason})")
    log(f"detail_pages={len(records)}")
    return records
