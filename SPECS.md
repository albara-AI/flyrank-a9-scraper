# SPECS — A9 polite scraper (harness checklist)

One stage at a time: build it, run its checkpoint, tick the box, commit. Never start the next stage on a red checkpoint.

- [x] Stage 0 — classify the target (README section, robots check command)
- [ ] Stage 1 — fetch once, cache once (FETCH then CACHE HIT, size printed, no HTML dump)
- [ ] Stage 2 — find all three pages (catalogue_pages=3 discovered=60 unique_urls=60, twice)
- [ ] Stage 3 — extract raw records (8 keys incl. nulls, detail_pages=60)
- [ ] Stage 4 — clean, check, store (books.json == 60, numeric prices, https URLs, rerun still 60)
- [ ] Stage 5 — survive failures, report the run (fake URL -> failed_pages: 1, 60 records survive)
- [ ] Stage 6 — publish the evidence (README a stranger can run in 5 minutes)
