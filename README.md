# The polite scraper — FlyRank A9 (Python lane)

A small, polite scraping pipeline: it reads the first **3 catalogue pages** of [Books to Scrape](https://books.toscrape.com), visits all **60 book pages**, turns messy HTML into **clean, schema-checked JSON**, survives a broken page without crashing, and ends every run with an honest report.

```
fetch → extract → normalize → validate → store → report
```

## Run it (under 5 minutes)

Needs **Python 3.10+** and internet. Nothing paid, no accounts.

```bash
git clone https://github.com/albara-AI/flyrank-a9-scraper.git
cd flyrank-a9-scraper
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

You get three files in `output/`: `books.json` (60 records), `errors.json` (records that failed the schema, with the reason), and `run-report.json`. The first run takes about a minute because it waits between requests on purpose; a second run reads everything from `cache/` and finishes in under a second.

| Command | What it does |
|---|---|
| `python src/main.py` | Full run |
| `python src/main.py --check-robots` | Stage 0: request `robots.txt` once and print what happened |
| `python src/main.py --inject-broken-url` | Stage 5 proof: adds one made-up book URL; the run must still finish |
| `python -m pytest -q` | 40 offline tests (no network) |
| `python tests/replica_run.py` | The whole CLI against an offline replica of the site |

Exit code `0` means a clean run; `2` means the run finished but something failed (details in `run-report.json`).

## Target classification (Stage 0)

- **Site:** [Books to Scrape](https://books.toscrape.com), part of the toscrape.com sandbox.
- **Why this site:** toscrape.com describes Books to Scrape as a sandbox built for people to practise web scraping, and the site header itself says "We love being scraped!". That statement is the permission, and a site like this is the only kind this project touches.
- **Scope:** the first 3 catalogue pages only (`catalogue/page-1.html` to `page-3.html`) and the 60 book pages they link to. A cold run sends about 63 page requests; a cached rerun sends none.
- **robots.txt:** requested once with `python src/main.py --check-robots`. Result (checked 2026-10-28): no robots file found (HTTP 404). A missing file is not permission; the permission is the sandbox statement on toscrape.com.
- **Data collected:** public product facts for each book (title, price, availability, star rating, description) plus where and when each page was fetched. No personal data, no accounts, no logins.
- **Why it is appropriate here:** the owner built the site to be scraped, the scope is tiny, and every request is identified, has a timeout, and is spaced out.

> I will not reuse this code on another site without checking its rules and terms first.

## Politeness rules

All of them live in [`src/config.py`](src/config.py).

| Rule | Value | Why |
|---|---|---|
| User-agent | `FlyRankInternshipA9/1.0 (+https://github.com/albara-AI/flyrank-a9-scraper)` | A site owner reading their logs can see who we are and find us |
| Timeout | 10 seconds | A request gives up instead of hanging forever |
| Delay | 1 second between real requests (minimum required: 0.5 s) | Never hammer the site; cached pages need no delay |
| Status check | Only HTTP 200 is a page | Anything else is a failed fetch, never HTML to parse |
| Cache | Every page is saved to `cache/` once and reused | You can restart the script fifty times; the site feels it once |
| Retries | One retry after 2 s, only for timeouts and 5xx | 404 won't appear by asking again; 403 means "no", and asking again is rude |
| Scope | Stops after 3 catalogue pages, follows the site's own "next" link | No hardcoded URLs, no wandering |

## Record schema

Defined once with Pydantic in [`src/clean.py`](src/clean.py) (`extra="forbid"`: unknown fields are rejected too). Raw text and clean values live side by side.

| Field | Type | Notes |
|---|---|---|
| `title` | string, required | Full title from the book page (catalogue links are truncated) |
| `product_url` | string, `https://…` | Canonical URL, the record's identity; a book seen twice counts once |
| `price_text` | string | Raw, e.g. `"£51.77"` |
| `availability_text` | string | Raw, e.g. `"In stock (22 available)"` |
| `rating_text` | string | Raw, `"One"` … `"Five"` |
| `description` | string or `null` | `null` when the page has none; never invented |
| `source_page` | string, `https://…` | Provenance: the catalogue page that listed the book |
| `fetched_at` | ISO-8601 UTC | Provenance: when the site actually sent the page (kept through cache hits) |
| `price_gbp` | number > 0 | Clean value of `price_text` |
| `rating` | integer 1–5 | Clean value of `rating_text` |
| `in_stock` | boolean | From `availability_text` |
| `stock_count` | integer or `null` | From `availability_text` |

A record that fails the schema goes to `errors.json` with the reason and never reaches `books.json`. `books.json` is an upsert keyed by `product_url` and written atomically, so rerunning gives the same 60 records, not 120 (idempotency).

## Run report

{
  "started_at": "2026-10-28T08:57:16Z",
  "finished_at": "2026-10-28T08:58:19Z",
  "duration_seconds": 63.12,
  "target": "https://books.toscrape.com/catalogue/page-1.html",
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "injected_urls": 0,
  "network_requests": 63,
  "pages_fetched": 63,
  "cache_hits": 0,
  "retries": 0,
  "detail_pages": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "books_json_total": 60,
  "failures": []
}

## Why no browser

The data is already in the HTML the server sends (view-source shows the prices and descriptions), so a browser would only add cost: a heavy engine to install, seconds of rendering per page, and more load on the site, for zero extra data.

## How it was verified offline

`tests/replica.py` is an offline replica of Books to Scrape served through a fake `requests` transport, so the URLs stay `https://books.toscrape.com/…` and the code under test is the real code. It reproduces the live site's traps: truncated title links, a second price inside the product-information table, books with no description, and a `Content-Type` with no charset (which makes `resp.text` show `Â£51.77`; this project decodes the raw bytes as UTF-8 instead). Page 1 uses the real titles and prices; pages 2–3 are generated.

The 40 tests cover politeness (user-agent, timeout, delay, cache, retry rules), parsing, the schema, idempotency, and failure handling. Every rule was checked by breaking the code on purpose (11 deliberate mutations); each one makes at least one test fail.

## One honest limitation

The selectors are tied to Books to Scrape's current HTML. If the layout changes, pages fail loudly (a `ParseError` counted in `failed_pages`, or schema errors in `errors.json`) rather than producing wrong data, but they do fail; nothing heals itself. Also, the cache never expires: delete `cache/` to collect fresh data.

Descriptions are stored exactly as the site serves them, including its own quirks: a repeated opening sentence, words joined where line breaks used to be (e.g. "treetopDon't", confirmed in the cached HTML), and a trailing "...more". Cleaning them is left to whoever consumes the data.

## Ethics note

Draft: rewrite this in your own words before submitting.

Use an official API whenever one exists; scraping is for when there isn't one. Never get around logins, paywalls, CAPTCHAs, or blocks; if a site says no, the answer is no. Collect only the fields you actually need, identify yourself honestly, and keep your request rate low enough that the site owner would never notice you.

## Project layout

```
src/
  main.py      CLI entry point (51 lines)
  config.py    every politeness rule and path
  fetcher.py   Stage 1: polite fetching + cache
  parse.py     Stages 2–3: catalogue discovery, book extraction
  clean.py     Stage 4: normalization + Pydantic schema
  store.py     atomic JSON writes, idempotent upsert
  pipeline.py  the stages wired together + run report
tests/         offline replica + 40 tests
SPECS.md       stage checklist used while building
```
