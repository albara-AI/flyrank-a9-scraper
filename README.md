# The polite scraper — FlyRank A9 (Python lane)

## Target classification (Stage 0)

- **Site:** [Books to Scrape](https://books.toscrape.com), part of the toscrape.com sandbox.
- **Why this site:** toscrape.com describes Books to Scrape as a sandbox built for people to practise web scraping, and the site header itself says "We love being scraped!". That statement is the permission, and a site like this is the only kind this project touches.
- **Scope:** the first 3 catalogue pages only (`catalogue/page-1.html` to `page-3.html`) and the 60 book pages they link to. A cold run sends about 63 page requests; a cached rerun sends none.
- **robots.txt:** requested once with `python src/main.py --check-robots`. Result: TODO (paste the printed result after your first real run).
- **Data collected:** public product facts for each book (title, price, availability, star rating, description) plus where and when each page was fetched. No personal data, no accounts, no logins.
- **Why it is appropriate here:** the owner built the site to be scraped, the scope is tiny, and every request is identified, has a timeout, and is spaced out.

> I will not reuse this code on another site without checking its rules and terms first.
