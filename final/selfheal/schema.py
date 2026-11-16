"""Product contract and fill rate."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

TRACKED_FIELDS: tuple[str, ...] = (
    "title",
    "price",
    "currency",
    "availability",
    "rating",
    "review_count",
    "brand",
    "sku",
)


class ProductSchema(BaseModel):
    """Fields every tier has to aim at. Title is the only required value."""

    model_config = ConfigDict(extra="ignore")

    title: str
    price: str | None = None
    currency: str | None = None
    availability: str | None = None
    rating: float | None = None
    review_count: int | None = None
    brand: str | None = None
    sku: str | None = None


def is_filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def fill_rate(product: ProductSchema, fields: tuple[str, ...] = TRACKED_FIELDS) -> float:
    filled = sum(1 for name in fields if is_filled(getattr(product, name)))
    if not fields:
        return 0.0
    return filled / len(fields)


def field_nulls(
    product: ProductSchema | None, fields: tuple[str, ...] = TRACKED_FIELDS
) -> dict[str, bool]:
    nulls: dict[str, bool] = {}
    for name in fields:
        value = None if product is None else getattr(product, name)
        nulls[name] = not is_filled(value)
    return nulls


def as_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    return float(match.group(0))


def as_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    return int(digits)


def currency_from_price(price: str | None, explicit: str | None = None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip().upper()
    if not price:
        return None
    if "$" in price:
        return "USD"
    if "£" in price:
        return "GBP"
    if "€" in price:
        return "EUR"
    return None


def price_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"([$£€]\s?\d[\d,]*(?:\.\d{2})?)", text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    bare = re.search(r"\d[\d,]*(?:\.\d{2})?", text)
    if bare and len(text) <= 16:
        return bare.group(0)
    return None


@dataclass
class Result:
    tier: str
    product: ProductSchema | None
    fill_rate: float
    field_nulls: dict[str, bool]
    error: str | None = None


def success_result(tier: str, product: ProductSchema) -> Result:
    return Result(
        tier=tier,
        product=product,
        fill_rate=fill_rate(product),
        field_nulls=field_nulls(product),
    )


def failed_result(tier: str, error: str) -> Result:
    return Result(
        tier=tier,
        product=None,
        fill_rate=0.0,
        field_nulls=field_nulls(None),
        error=error,
    )
