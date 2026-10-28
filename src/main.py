"""A9 polite scraper — entry point.

    python src/main.py                      run: 3 catalogue pages -> 60 books -> output/
    python src/main.py --check-robots       Stage 0: request robots.txt once
    python src/main.py --inject-broken-url  Stage 5: prove one bad page can't kill the run

Exit codes: 0 = clean run, 2 = finished but something failed (see run-report.json).
"""
import argparse
import sys

from config import Settings
from fetcher import PoliteFetcher
from pipeline import run

BROKEN_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0/index.html"


def check_robots(fetcher: PoliteFetcher, settings: Settings) -> int:
    resp = fetcher.probe(settings.robots_url)
    if resp.status_code == 200:
        print(f"robots.txt: found (HTTP 200)\n{resp.text.strip() or '(empty file)'}")
    elif resp.status_code == 404:
        print("robots.txt: no robots file found (HTTP 404).")
        print("A missing file is not permission; the permission is the sandbox statement on toscrape.com.")
    else:
        print(f"robots.txt: HTTP {resp.status_code}; write this down and stop to think before scraping.")
    return 0


def main(argv=None, session=None, settings=None) -> int:
    parser = argparse.ArgumentParser(description="Polite Books to Scrape scraper (FlyRank A9)")
    parser.add_argument("--check-robots", action="store_true", help="Stage 0: request robots.txt once")
    parser.add_argument("--inject-broken-url", action="store_true",
                        help="Stage 5: add one made-up book URL to prove failures are survived")
    args = parser.parse_args(argv)
    settings = settings or Settings()
    fetcher = PoliteFetcher(settings, session=session)
    if args.check_robots:
        return check_robots(fetcher, settings)

    report = run(settings, fetcher, extra_urls=[BROKEN_URL] if args.inject_broken_url else [])
    print(f"done in {report['duration_seconds']}s | network_requests={report['network_requests']} "
          f"cache_hits={report['cache_hits']} failed_pages={report['failed_pages']} "
          f"-> {settings.output_dir / 'run-report.json'}")
    clean = report["failed_pages"] == 0 and report["invalid_records"] == 0
    return 0 if clean else 2


if __name__ == "__main__":
    sys.exit(main())
