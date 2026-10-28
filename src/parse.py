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


RAW_KEYS = ("title", "product_url", "price_text", "availability_text",
            "rating_text", "description", "source_page", "fetched_at")


def _text(el) -> str | None:
    """Visible text with whitespace collapsed; None when the element is missing or empty."""
    if el is None:
        return None
    return " ".join(el.get_text().split()) or None


def parse_book(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Stage 3: one book page -> one raw record (strings exactly as the page shows them)."""
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("article.product_page")
    main = product.select_one("div.product_main") if product else None
    if main is None:
        raise ParseError("no product area (article.product_page > div.product_main) on book page")
    rating = main.select_one("p.star-rating")
    rating_words = [c for c in rating.get("class", []) if c != "star-rating"] if rating else []
    description_header = product.select_one("#product_description")
    return {
        "title": _text(main.select_one("h1")),
        "product_url": product_url,
        # Aim inside the product area: the page has more prices in its info table.
        "price_text": _text(main.select_one("p.price_color")),
        "availability_text": _text(main.select_one("p.availability")),
        "rating_text": rating_words[0] if rating_words else None,
        # Some books have no description: store None, never invent text.
        "description": _text(description_header.find_next_sibling("p")) if description_header else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
