"""Turn scraper JSON, CSS hits, or model text into ProductSchema."""

from __future__ import annotations

from typing import Any

from selfheal.schema import ProductSchema, as_float, as_int, currency_from_price, price_text


def _text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def product_from_mapping(data: dict[str, Any]) -> ProductSchema | None:
    title = _text(data, "title", "name")
    if title is None:
        return None
    raw_price = data.get("price")
    if raw_price is None:
        raw_price = data.get("rawPrice")
    price = price_text(raw_price)
    if price is None and isinstance(raw_price, str) and raw_price.strip():
        price = raw_price.strip()
    currency = currency_from_price(price, _text(data, "currency", "price_currency"))
    availability = _text(data, "availability", "stock")
    if availability is None and isinstance(data.get("inStock"), bool):
        availability = "In Stock" if data["inStock"] else "Out of Stock"
    sku = _text(data, "sku", "asin", "product_id", "itemId")
    parent = data.get("parentAsin")
    if sku is None and isinstance(parent, str) and parent.strip():
        sku = parent.strip()
    if sku is None and isinstance(parent, list):
        for item in parent:
            if isinstance(item, str) and item.strip():
                sku = item.strip()
                break
    brand = _text(data, "brand")
    rating_value = data.get("rating")
    if rating_value in (None, ""):
        rating_value = data.get("ratings")
    if rating_value in (None, ""):
        rating_value = data.get("customerReview")
    return ProductSchema(
        title=title,
        price=price,
        currency=currency,
        availability=availability,
        rating=as_float(rating_value),
        review_count=as_int(
            data.get("review_count")
            or data.get("reviews_count")
            or data.get("reviewsCount")
            or data.get("customerReviewCount")
        ),
        brand=brand,
        sku=sku,
    )
