"""Writing results: atomic files, and an idempotent upsert keyed by canonical URL."""
import json
import os
from pathlib import Path

from clean import Book


def write_json(path: Path, data) -> None:
    """Write to a temp file, then swap it in: a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def upsert_books(path: Path, books: list[Book]) -> int:
    """Rerunning updates records, never duplicates them. Returns the total stored."""
    stored = {}
    if path.exists():
        stored = {item["product_url"]: item for item in json.loads(path.read_text(encoding="utf-8"))}
    for book in books:
        stored[book.product_url] = book.model_dump(mode="json")
    write_json(path, list(stored.values()))
    return len(stored)
