"""Offline replica of Books to Scrape, served through a fake requests transport.

Why: checkpoints must be runnable without touching the real site (and in sandboxes
with no internet). URLs stay exactly https://books.toscrape.com/..., only the
transport is fake, so the scraper code under test is the real code.

Fidelity notes (copied from the live site's structure):
- each catalogue page has 20 books, each linked twice (image + title link)
- the title link text is truncated; the full title is only on the book page
- book pages show a second price inside the Product Information table
- Content-Type is "text/html" with no charset, so requests guesses ISO-8859-1
  and resp.text turns "£51.77" into "Â£51.77" (the classic trap)
- robots.txt does not exist (404)
Page 1 uses the real titles and prices; pages 2-3 are generated.
"""
import html
from urllib.parse import urlsplit

import requests
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

BASE = "https://books.toscrape.com"

PAGE_1 = [  # (slug, title, price) as published on catalogue/page-1.html
    ("a-light-in-the-attic_1000", "A Light in the Attic", "51.77"),
    ("tipping-the-velvet_999", "Tipping the Velvet", "53.74"),
    ("soumission_998", "Soumission", "50.10"),
    ("sharp-objects_997", "Sharp Objects", "47.82"),
    ("sapiens-a-brief-history-of-humankind_996", "Sapiens: A Brief History of Humankind", "54.23"),
    ("the-requiem-red_995", "The Requiem Red", "22.65"),
    ("the-dirty-little-secrets-of-getting-your-dream-job_994", "The Dirty Little Secrets of Getting Your Dream Job", "33.34"),
    ("the-coming-woman-a-novel-based-on-the-life-of-the-infamous-feminist-victoria-woodhull_993", "The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull", "17.93"),
    ("the-boys-in-the-boat-nine-americans-and-their-epic-quest-for-gold-at-the-1936-berlin-olympics_992", "The Boys in the Boat: Nine Americans and Their Epic Quest for Gold at the 1936 Berlin Olympics", "22.60"),
    ("the-black-maria_991", "The Black Maria", "52.15"),
    ("starving-hearts-triangular-trade-trilogy-1_990", "Starving Hearts (Triangular Trade Trilogy, #1)", "13.99"),
    ("shakespeares-sonnets_989", "Shakespeare's Sonnets", "20.66"),
    ("set-me-free_988", "Set Me Free", "17.46"),
    ("scott-pilgrims-precious-little-life-scott-pilgrim-1_987", "Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)", "52.29"),
    ("rip-it-up-and-start-again_986", "Rip it Up and Start Again", "35.02"),
    ("our-band-could-be-your-life-scenes-from-the-american-indie-underground-1981-1991_985", "Our Band Could Be Your Life: Scenes from the American Indie Underground, 1981-1991", "57.25"),
    ("olio_984", "Olio", "23.88"),
    ("mesaerion-the-best-science-fiction-stories-1800-1849_983", "Mesaerion: The Best Science Fiction Stories 1800-1849", "37.59"),
    ("libertarianism-for-beginners_982", "Libertarianism for Beginners", "51.33"),
    ("its-only-the-himalayas_981", "It's Only the Himalayas", "45.17"),
]
RATINGS = ["One", "Two", "Three", "Four", "Five"]
NO_DESCRIPTION = {"replica-book-21_980"}          # the site really has books like this
ODD_TITLE = "replica-book-33_968"                  # entities + non-ASCII in the title


def _books():
    books = []
    for slug, title, price in PAGE_1:
        books.append({"slug": slug, "title": title, "price": price})
    for n in range(21, 61):
        slug = f"replica-book-{n}_{1001 - n}"
        title = "Café Society & the Bookshop <Vol. 2>" if slug == ODD_TITLE else f"Replica Book {n}"
        books.append({"slug": slug, "title": title, "price": f"{10 + (n * 377 % 4600) / 100:.2f}"})
    for i, b in enumerate(books):
        b["rating"] = RATINGS[(i * 3 + 2) % 5]
        b["stock"] = 22 - (i % 7)
        b["page"] = i // 20 + 1
    return books


def _short(title):
    words = title.split()
    return title if len(words) <= 4 else " ".join(words[:4]) + " ..."


def catalogue_html(page, books):
    items = []
    for b in books:
        t = html.escape(b["title"], quote=True)
        items.append(f"""
            <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
    <article class="product_pod">
            <div class="image_container">
                    <a href="{b['slug']}/index.html"><img src="../media/cache/x.jpg" alt="{t}" class="thumbnail"></a>
            </div>
                <p class="star-rating {b['rating']}"><i class="icon-star"></i></p>
            <h3><a href="{b['slug']}/index.html" title="{t}">{html.escape(_short(b['title']))}</a></h3>
            <div class="product_price">
        <p class="price_color">£{b['price']}</p>
<p class="instock availability">
    <i class="icon-ok"></i>
        In stock
</p>
    <form><button type="submit" class="btn btn-primary btn-block">Add to basket</button></form>
            </div>
    </article>
</li>""")
    prev = f'<li class="previous"><a href="page-{page - 1}.html">previous</a></li>' if page > 1 else ""
    return f"""<!DOCTYPE html>
<html lang="en-us" class="no-js"><head><title>All products | Books to Scrape - Sandbox</title></head>
<body id="default" class="default">
<header class="header container-fluid"><div class="page_inner"><div class="row">
<div class="col-sm-8 h1"><a href="../index.html">Books to Scrape</a><small> We love being scraped!</small></div>
</div></div></header>
<div class="container-fluid page"><div class="page_inner">
<div class="row"><aside class="sidebar col-sm-4 col-md-3"><ul class="nav nav-list"><li><a href="category/books_1/index.html">Books</a></li></ul></aside>
<div class="col-sm-8 col-md-9"><div class="page-header action"><h1>All products</h1></div>
<form method="get" class="form-horizontal"><strong>1000</strong> results - showing <strong>{(page - 1) * 20 + 1}</strong> to <strong>{page * 20}</strong>.</form>
<section><div><ol class="row">{''.join(items)}
</ol><div><ul class="pager">
    {prev}
    <li class="current">Page {page} of 50</li>
    <li class="next"><a href="page-{page + 1}.html">next</a></li>
</ul></div></div></section></div></div></div></div></body></html>""".encode()


def book_html(b):
    t = html.escape(b["title"])
    desc = "" if b["slug"] in NO_DESCRIPTION else f"""
<div id="product_description" class="sub-header"><h2>Product Description</h2></div>
<p>{t} is a replica description with   extra
    whitespace, written for offline checkpoints. ...more</p>"""
    return f"""<!DOCTYPE html>
<html lang="en-us" class="no-js"><head><title>{t} | Books to Scrape - Sandbox</title></head>
<body id="default" class="default"><div class="container-fluid page"><div class="page_inner">
<ul class="breadcrumb"><li><a href="../../index.html">Home</a></li><li class="active">{t}</li></ul>
<div id="content_inner">
<article class="product_page"><!-- Start of product page -->
<div class="row">
<div class="col-sm-6"><div id="product_gallery" class="carousel"><img src="../../media/cache/x.jpg" alt="{t}" /></div></div>
<div class="col-sm-6 product_main">
    <h1>{t}</h1>
<p class="price_color">£{b['price']}</p>
<p class="instock availability">
    <i class="icon-ok"></i>

        In stock ({b['stock']} available)

</p>
    <p class="star-rating {b['rating']}">
        <i class="icon-star"></i><i class="icon-star"></i>
    </p>
    <hr/>
<div class="alert alert-warning" role="alert"><strong>Warning!</strong> This is a demo website for web scraping purposes.</div>
</div></div>{desc}
<div class="sub-header"><h2>Product Information</h2></div>
<table class="table table-striped">
<tr><th>UPC</th><td>replica{b['stock']}</td></tr>
<tr><th>Price (excl. tax)</th><td>£{b['price']}</td></tr>
<tr><th>Price (incl. tax)</th><td>£{b['price']}</td></tr>
<tr><th>Tax</th><td>£0.00</td></tr>
<tr><th>Availability</th><td>In stock ({b['stock']} available)</td></tr>
</table>
</article></div></div></div></body></html>""".encode()


NOT_FOUND = b"<html><head><title>404 Not Found</title></head><body><h1>Not Found</h1></body></html>"


def build_site():
    books = _books()
    site = {}
    for page in (1, 2, 3):  # page-4.html is deliberately missing: a correct scraper never asks
        site[f"/catalogue/page-{page}.html"] = catalogue_html(page, [b for b in books if b["page"] == page])
    for b in books:
        site[f"/catalogue/{b['slug']}/index.html"] = book_html(b)
    return site


class ReplicaAdapter(BaseAdapter):
    """Answers like the real server would, and remembers every request it got."""

    def __init__(self, site, fail_once=(), timeout_once=(), always_fail=()):
        super().__init__()
        self.site = site
        self.fail_once, self.timeout_once = set(fail_once), set(timeout_once)
        self.always_fail = set(always_fail)
        self.log = []

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        path = urlsplit(request.url).path
        self.log.append({"path": path, "user_agent": request.headers.get("User-Agent"), "timeout": timeout})
        if timeout is None:
            raise AssertionError(f"request without a timeout: {path}")
        if path in self.timeout_once:
            self.timeout_once.discard(path)
            raise requests.ReadTimeout(f"replica timeout for {path}")
        if path in self.fail_once:
            self.fail_once.discard(path)
            return self._response(request, 503, b"<h1>Service Unavailable</h1>")
        if path in self.always_fail:
            return self._response(request, 500, b"<h1>Internal Server Error</h1>")
        body = self.site.get(path)
        return self._response(request, 404, NOT_FOUND) if body is None else self._response(request, 200, body)

    def _response(self, request, status, body):
        resp = requests.Response()
        resp.status_code, resp._content, resp.url, resp.request = status, body, request.url, request
        resp.headers = CaseInsensitiveDict({"Content-Type": "text/html", "Content-Length": str(len(body))})
        resp.encoding = get_encoding_from_headers(resp.headers)  # ISO-8859-1, like the real server
        return resp

    def close(self):
        pass


def replica_session(**faults):
    """A requests.Session whose https://books.toscrape.com/ traffic goes to the replica."""
    adapter = ReplicaAdapter(build_site(), **faults)
    session = requests.Session()
    session.mount(BASE + "/", adapter)
    return session, adapter
