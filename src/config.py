"""Every politeness rule and every path lives here, in one place the README can point at."""
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/albara-AI/flyrank-a9-scraper"  # change if your repo name differs


@dataclass(frozen=True)
class Settings:
    start_url: str = "https://books.toscrape.com/catalogue/page-1.html"
    robots_url: str = "https://books.toscrape.com/robots.txt"
    max_catalogue_pages: int = 3
    user_agent: str = f"FlyRankInternshipA9/1.0 (+{REPO_URL})"
    timeout_seconds: float = 10.0     # a request gives up instead of hanging forever
    delay_seconds: float = 1.0        # between real requests (assignment minimum: 0.5)
    retry_wait_seconds: float = 2.0   # one retry, only for timeouts and 5xx
    cache_dir: Path = PROJECT_ROOT / "cache"
    output_dir: Path = PROJECT_ROOT / "output"
