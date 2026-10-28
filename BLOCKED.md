# BLOCKED: real-site run not done yet

The build environment had no network access to books.toscrape.com, so every checkpoint was verified against the offline replica (`tests/replica.py`, 40 tests, `python tests/replica_run.py`). Nothing below was guessed; it needs a machine with internet.

To unblock (about 3 minutes):

1. `python src/main.py --check-robots` → paste the printed result into README "Target classification".
2. `python src/main.py` → expect `catalogue_pages=3 discovered=60 unique_urls=60` and `valid_records=60`. Copy `output/run-report.json` into README "Run report" now.
3. `python src/main.py` again → expect `network_requests=0 cache_hits=63`.
4. `python src/main.py --inject-broken-url` → expect `failed_pages=1` and `books.json` still 60.
5. `python src/main.py` once more (leaves a clean report), commit `output/books.json`, `output/errors.json`, `output/run-report.json` as the sample output.
6. Tick Stage 6 in SPECS.md, delete this file, commit, push.
