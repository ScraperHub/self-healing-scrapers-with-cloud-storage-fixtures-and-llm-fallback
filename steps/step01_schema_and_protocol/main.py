"""Show the contract: a full product clears the fill-rate bar."""

from __future__ import annotations

from extractor import Extractor
from schema import ProductSchema, fill_rate


class StaticExtractor:
    tier = "static"

    def extract(self, page: str) -> ProductSchema:
        return ProductSchema(
            title=page,
            price="$98.00",
            currency="USD",
            availability="In stock",
            rating=4.8,
            review_count=120,
            brand="Allbirds",
            sku="TR-M",
        )


def main() -> int:
    extractor: Extractor = StaticExtractor()
    product = extractor.extract("Men's Tree Runner")
    rate = fill_rate(product)
    print(f"tier={extractor.tier} fill={rate:.2f} title={product.title}")
    if rate < 0.75 or not product.title:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
