"""A9 polite scraper — entry point.

    python src/main.py                  run the scraper
    python src/main.py --check-robots   Stage 0: request robots.txt once
"""
import argparse
import json
import sys

from config import Settings
from fetcher import PoliteFetcher
from pipeline import discover, extract


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
    args = parser.parse_args(argv)
    settings = settings or Settings()
    fetcher = PoliteFetcher(settings, session=session)
    if args.check_robots:
        return check_robots(fetcher, settings)
    failures = []
    found = discover(settings, fetcher, failures)
    raw = extract(found["sources"], fetcher, failures)
    if raw:
        print("sample raw record:\n" + json.dumps(raw[0], indent=2, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
