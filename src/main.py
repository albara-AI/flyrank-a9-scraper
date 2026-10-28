"""A9 polite scraper — entry point.

Stage 0 command:  python src/main.py --check-robots
"""
import argparse
import sys

import requests

from config import Settings


def check_robots(settings: Settings) -> int:
    """Request robots.txt exactly once, identified, with a timeout, and say what happened."""
    resp = requests.get(
        settings.robots_url,
        headers={"User-Agent": settings.user_agent},
        timeout=settings.timeout_seconds,
    )
    if resp.status_code == 200:
        print(f"robots.txt: found (HTTP 200)\n{resp.text.strip() or '(empty file)'}")
    elif resp.status_code == 404:
        print("robots.txt: no robots file found (HTTP 404).")
        print("A missing file is not permission; the permission is the sandbox statement on toscrape.com.")
    else:
        print(f"robots.txt: HTTP {resp.status_code}; write this down and stop to think before scraping.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Polite Books to Scrape scraper (FlyRank A9)")
    parser.add_argument("--check-robots", action="store_true", help="Stage 0: request robots.txt once")
    args = parser.parse_args(argv)
    settings = Settings()
    if args.check_robots:
        return check_robots(settings)
    print(f"Target: {settings.start_url} (first {settings.max_catalogue_pages} catalogue pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
