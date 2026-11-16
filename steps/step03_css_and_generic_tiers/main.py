"""CSS on the saved page, then generic-extractor JSON when selectors miss."""

from __future__ import annotations

from pathlib import Path

from css_tier import apply_selectors, load_selectors
from generic_tier import product_from_generic

HERE = Path(__file__).resolve().parent
FIELDS = (
    "title",
    "price",
    "currency",
    "availability",
    "rating",
    "review_count",
    "brand",
    "sku",
)


def main() -> int:
    html = (HERE / "sample_allbirds.html").read_text(encoding="utf-8")
    selectors = load_selectors(HERE / "selectors.json")
    css_found = apply_selectors(html, selectors)
    css_rate = _rate(css_found)
    print(f"tier=css fill={css_rate:.2f} title={css_found.get('title', '')}")
    generic = product_from_generic(
        {
            "title": "",
            "headings": ["Men's Tree Runner"],
            "main_content": "Price $100. In stock.",
        }
    )
    generic_rate = _rate(generic)
    print(f"tier=generic fill={generic_rate:.2f} title={generic.get('title', '')}")
    if css_rate < 0.75 or not css_found.get("title"):
        return 1
    if generic_rate >= css_rate:
        return 1
    return 0


def _rate(found: dict[str, str]) -> float:
    filled = sum(1 for name in FIELDS if found.get(name, "").strip())
    return filled / len(FIELDS)


if __name__ == "__main__":
    raise SystemExit(main())
