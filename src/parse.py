"""Stages 2-3: a crawler finds the shelves, an extractor reads the labels."""
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup


class ParseError(Exception):
    """The page arrived but does not look like the page we expected."""

    @property
    def reason(self) -> str:
        return str(self)


def absolute(base_url: str, href: str) -> str:
    """Relative -> absolute with the URL tools (never string gluing), without #fragments."""
    return urldefrag(urljoin(base_url, href))[0]


def parse_catalogue(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Return (book URLs on this page, URL of the next page or None)."""
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("article.product_pod h3 a[href]")  # one link per book (the image link duplicates it)
    if not links:
        raise ParseError("no book links found on catalogue page")
    next_link = soup.select_one("ul.pager li.next a[href]")
    next_url = absolute(page_url, next_link["href"]) if next_link else None
    return [absolute(page_url, a["href"]) for a in links], next_url
