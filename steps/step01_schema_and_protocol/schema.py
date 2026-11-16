"""The product contract. Every tier fills this, or it does not count."""

from __future__ import annotations

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
