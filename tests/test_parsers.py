"""Parser and schema tests: fixtures only, no network."""
import pytest
from pydantic import ValidationError

from clean import Book, normalize, parse_price, validate
from parse import ParseError, absolute, parse_book, parse_catalogue
from replica import build_site

SITE = build_site()
PAGE_1 = "https://books.toscrape.com/catalogue/page-1.html"
ATTIC = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"


def book_page(slug):
    return SITE[f"/catalogue/{slug}/index.html"].decode("utf-8")


@pytest.mark.parametrize("text, expected", [
    ("£51.77", 51.77),
    ("Â£51.77", 51.77),        # what resp.text shows when the charset is guessed wrong
    ("  £ 13.99 ", 13.99),
    ("£10", 10.0),
    ("", None),
    (None, None),
])
def test_price_normalization(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("base, href, expected", [
    (PAGE_1, "a-light-in-the-attic_1000/index.html", ATTIC),
    ("https://books.toscrape.com/catalogue/category/books/poetry_23/index.html",
     "../../../a-light-in-the-attic_1000/index.html", ATTIC),
    (PAGE_1, "page-2.html", "https://books.toscrape.com/catalogue/page-2.html"),
    (PAGE_1, "a-light-in-the-attic_1000/index.html#reviews", ATTIC),
])
def test_relative_to_absolute(base, href, expected):
    assert absolute(base, href) == expected


def test_catalogue_gives_20_absolute_links_and_next():
    links, next_url = parse_catalogue(SITE["/catalogue/page-1.html"].decode(), PAGE_1)
    assert len(links) == 20 and len(set(links)) == 20
    assert links[0] == ATTIC
    assert all(link.startswith("https://") for link in links)
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


def test_full_title_comes_from_book_page_not_truncated_link():
    slug = "the-boys-in-the-boat-nine-americans-and-their-epic-quest-for-gold-at-the-1936-berlin-olympics_992"
    rec = parse_book(book_page(slug), "u", PAGE_1, "2026-10-28T00:00:00Z")
    assert rec["title"].endswith("1936 Berlin Olympics")


def test_missing_description_is_none_and_all_eight_keys_present():
    rec = parse_book(book_page("replica-book-21_980"), "u", PAGE_1, "2026-10-28T00:00:00Z")
    assert rec["description"] is None
    assert list(rec) == ["title", "product_url", "price_text", "availability_text",
                         "rating_text", "description", "source_page", "fetched_at"]


def test_whitespace_collapsed_and_entities_decoded():
    rec = parse_book(book_page("replica-book-33_968"), "u", PAGE_1, "2026-10-28T00:00:00Z")
    assert rec["title"] == "Café Society & the Bookshop <Vol. 2>"
    assert rec["availability_text"].startswith("In stock (")
    assert "  " not in rec["description"]


def test_price_comes_from_product_area_not_first_price_on_page():
    html = book_page("a-light-in-the-attic_1000").replace(
        '<div id="content_inner">', '<div id="content_inner"><p class="price_color">£999.99</p>')
    assert parse_book(html, ATTIC, PAGE_1, "2026-10-28T00:00:00Z")["price_text"] == "£51.77"


def test_malformed_page_raises_parse_error():
    with pytest.raises(ParseError):
        parse_book("<html><body><h1>Oops, maintenance</h1></body></html>", ATTIC, PAGE_1, "x")
    with pytest.raises(ParseError):
        parse_catalogue("<html><body>empty shelf</body></html>", PAGE_1)


def good_raw(**overrides):
    raw = parse_book(book_page("a-light-in-the-attic_1000"), ATTIC, PAGE_1, "2026-10-28T10:00:00Z")
    return {**raw, **overrides}


def test_normalize_adds_clean_values_next_to_raw_ones():
    rec = normalize(good_raw())
    assert (rec["price_text"], rec["price_gbp"]) == ("£51.77", 51.77)
    assert (rec["rating_text"], rec["rating"]) == ("Three", 3)
    assert (rec["in_stock"], rec["stock_count"]) == (True, 22)


@pytest.mark.parametrize("overrides, field", [
    ({"price_text": None}, "price_text"),
    ({"price_text": "£0.00"}, "price_gbp"),
    ({"rating_text": "Seven"}, "rating"),
    ({"product_url": "http://books.toscrape.com/x"}, "product_url"),
    ({"title": None}, "title"),
    ({"fetched_at": "yesterday"}, "fetched_at"),
])
def test_bad_records_go_to_errors_with_a_reason(overrides, field):
    good, bad = validate([good_raw(**overrides)])
    assert good == [] and len(bad) == 1
    assert field in bad[0]["reason"] and bad[0]["raw"]["product_url"]


def test_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Book.model_validate({**normalize(good_raw()), "surprise": 1})


def test_valid_record_serializes_with_utc_z():
    good, bad = validate([good_raw()])
    assert bad == []
    assert good[0].model_dump(mode="json")["fetched_at"] == "2026-10-28T10:00:00Z"
