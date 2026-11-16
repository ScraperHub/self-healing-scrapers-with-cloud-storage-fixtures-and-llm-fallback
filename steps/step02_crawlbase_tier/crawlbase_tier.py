"""Map a built-in scraper payload onto the product schema."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProductSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    price: str | None = None
    currency: str | None = None
    availability: str | None = None
    rating: float | None = None
    review_count: int | None = None
    brand: str | None = None
    sku: str | None = None


def product_from_scraper(data: dict[str, Any]) -> ProductSchema | None:
    title = _text(data, "title", "name")
    if title is None:
        return None
    raw_price = data.get("price")
    if raw_price is None:
        raw_price = data.get("rawPrice")
    price = _price(raw_price)
    return ProductSchema(
        title=title,
        price=price,
        currency=_currency(price, _text(data, "currency")),
        availability=_availability(data),
        rating=_float(data.get("customerReview") or data.get("rating")),
        review_count=_int(data.get("customerReviewCount") or data.get("review_count")),
        brand=_text(data, "brand"),
        sku=_sku(data),
    )


def fill_rate(product: ProductSchema) -> float:
    fields = (
        "title",
        "price",
        "currency",
        "availability",
        "rating",
        "review_count",
        "brand",
        "sku",
    )
    filled = 0
    for name in fields:
        value = getattr(product, name)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        filled += 1
    return filled / len(fields)


def _text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _price(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"([$£€]?\s?\d[\d,]*(?:\.\d{2})?)", text)
    if match is None:
        return None
    return re.sub(r"\s+", "", match.group(1))


def _currency(price: str | None, explicit: str | None) -> str | None:
    if explicit and any(symbol in explicit for symbol in "$£€"):
        if "$" in explicit:
            return "USD"
        if "£" in explicit:
            return "GBP"
        return "EUR"
    if not price:
        return None
    if "$" in price:
        return "USD"
    if "£" in price:
        return "GBP"
    if "€" in price:
        return "EUR"
    return None


def _availability(data: dict[str, Any]) -> str | None:
    text = _text(data, "availability", "stock")
    if text:
        return text
    if isinstance(data.get("inStock"), bool):
        return "In Stock" if data["inStock"] else "Out of Stock"
    return None


def _sku(data: dict[str, Any]) -> str | None:
    sku = _text(data, "sku", "asin", "itemId")
    if sku:
        return sku
    parent = data.get("parentAsin")
    if isinstance(parent, list):
        for item in parent:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _float(value: object) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    return float(match.group(0))


def _int(value: object) -> int | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    return int(digits)
