"""Shared builders for offline tests."""

from __future__ import annotations

from selfheal.extractors.page import Page
from selfheal.schema import ProductSchema


def sample_selectors() -> dict[str, str]:
    return {
        "title": "h1.product-title",
        "price": ".product-price",
        "currency": ".product-currency",
        "availability": ".product-availability",
        "rating": ".product-rating",
        "review_count": ".product-reviews",
        "brand": ".product-brand",
        "sku": ".product-sku",
    }


def sample_html() -> str:
    return """
    <html><body>
      <h1 class="product-title">Tree Runner</h1>
      <span class="product-price">$98.00</span>
      <span class="product-currency">USD</span>
      <span class="product-availability">In stock</span>
      <span class="product-rating">4.8</span>
      <span class="product-reviews">120 reviews</span>
      <span class="product-brand">Allbirds</span>
      <span class="product-sku">TR-M</span>
      <script>var secret = 1;</script>
    </body></html>
    """


def sample_page(**overrides: object) -> Page:
    data = {
        "url": "https://www.allbirds.com/products/mens-tree-runners",
        "site": "allbirds",
        "html": sample_html(),
        "original_status": 200,
        "cb_status": 200,
    }
    data.update(overrides)
    return Page(**data)  # type: ignore[arg-type]


def full_product() -> ProductSchema:
    return ProductSchema(
        title="Tree Runner",
        price="$98.00",
        currency="USD",
        availability="In stock",
        rating=4.8,
        review_count=120,
        brand="Allbirds",
        sku="TR-M",
    )
