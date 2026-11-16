"""Target sites. Built-in scrapers cover Amazon and Walmart. Allbirds does not."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    name: str
    scraper: str | None
    watch_tier: str
    confirm_tier: str
    urls: tuple[str, ...]
    min_fill_rate: float = 0.75


SITES: dict[str, Site] = {
    "amazon": Site(
        name="amazon",
        scraper="amazon-product-details",
        watch_tier="crawlbase",
        confirm_tier="llm",
        urls=(
            "https://www.amazon.com/dp/B0CHX2XFLN",
            "https://www.amazon.com/dp/0134757599",
            "https://www.amazon.com/dp/0132350882",
            "https://www.amazon.com/dp/0201633612",
            "https://www.amazon.com/dp/0134685997",
        ),
    ),
    "walmart": Site(
        name="walmart",
        scraper="walmart-product-details",
        watch_tier="crawlbase",
        confirm_tier="llm",
        urls=(
            "https://www.walmart.com/ip/3551794083",
            "https://www.walmart.com/ip/10450114",
            "https://www.walmart.com/ip/8886020987",
            "https://www.walmart.com/ip/10762707702",
            "https://www.walmart.com/ip/1095568875",
        ),
    ),
    "allbirds": Site(
        name="allbirds",
        scraper=None,
        watch_tier="css",
        confirm_tier="llm",
        urls=(
            "https://www.allbirds.com/products/mens-tree-runners",
            "https://www.allbirds.com/products/womens-tree-runners",
            "https://www.allbirds.com/products/mens-wool-runners",
            "https://www.allbirds.com/products/womens-tree-breezers",
            "https://www.allbirds.com/products/womens-tree-gliders",
        ),
    ),
}


def get_site(name: str) -> Site:
    try:
        return SITES[name]
    except KeyError as exc:
        known = ", ".join(sorted(SITES))
        raise KeyError(f"Unknown site '{name}'. Known sites: {known}") from exc
