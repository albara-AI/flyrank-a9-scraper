"""Stage 4: raw strings are ingredients, the schema is the recipe."""
import re

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

HTTPS = r"^https://\S+$"
RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
NUMBER = re.compile(r"\d+(?:\.\d+)?")
STOCK = re.compile(r"\((\d+) available\)")


class Book(BaseModel):
    """The shape of a finished record. Raw text and clean values live side by side."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    product_url: str = Field(pattern=HTTPS)          # canonical URL = the record's identity
    price_text: str = Field(min_length=1)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(min_length=1)
    description: str | None = None                    # optional: some books have none
    source_page: str = Field(pattern=HTTPS)
    fetched_at: AwareDatetime
    price_gbp: float = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    in_stock: bool
    stock_count: int | None = Field(default=None, ge=0)


def parse_price(text: str | None) -> float | None:
    """'£51.77' -> 51.77. Reads only the number, so even a mis-decoded 'Â£51.77' is safe."""
    match = NUMBER.search(text or "")
    return float(match.group()) if match else None


def normalize(raw: dict) -> dict:
    availability = raw.get("availability_text") or ""
    stock = STOCK.search(availability)
    return {
        **raw,
        "price_gbp": parse_price(raw.get("price_text")),
        "rating": RATING_WORDS.get(raw.get("rating_text") or ""),
        "in_stock": availability.lower().startswith("in stock"),
        "stock_count": int(stock.group(1)) if stock else None,
    }


def validate(raw_records: list[dict]) -> tuple[list[Book], list[dict]]:
    """Every record passes the schema or goes to errors.json with the reason. Nothing sneaks in."""
    good, bad = [], []
    for raw in raw_records:
        try:
            good.append(Book.model_validate(normalize(raw)))
        except ValidationError as exc:
            reason = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
            bad.append({"product_url": raw.get("product_url"), "reason": reason, "raw": raw})
    return good, bad
