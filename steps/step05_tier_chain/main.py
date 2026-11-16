"""A full page stops at CSS. A broken page falls through to the LLM tier."""

from __future__ import annotations

from chain import TierChain
from fill_rate import ProductSchema

FULL_PAGE = (
    "title=Men's Tree Runner;price=$100;currency=USD;availability=In stock;brand=Allbirds;sku=TR-M"
)
BROKEN_PAGE = "markdown=Men's Tree Runner|$100|Allbirds|TR-M"


class CssTier:
    tier = "css"

    def extract(self, page: str) -> ProductSchema | None:
        if not page.startswith("title="):
            return None
        fields = dict(part.split("=", 1) for part in page.split(";"))
        return ProductSchema(
            title=fields["title"],
            price=fields.get("price"),
            currency=fields.get("currency"),
            availability=fields.get("availability"),
            brand=fields.get("brand"),
            sku=fields.get("sku"),
        )


class LlmTier:
    tier = "llm"

    def extract(self, page: str) -> ProductSchema | None:
        if "markdown=" not in page:
            return None
        title, price, brand, sku = page.split("markdown=", 1)[1].split("|")
        return ProductSchema(
            title=title,
            price=price,
            currency="USD",
            availability="In stock",
            brand=brand,
            sku=sku,
        )


def main() -> int:
    chain = TierChain([CssTier(), LlmTier()])
    first = chain.run(FULL_PAGE)
    second = chain.run(BROKEN_PAGE)
    if first.winner is None or second.winner is None:
        print("chain produced no winner")
        return 1
    print(
        f"full winner={first.winner.tier} attempts={len(first.attempts)} "
        f"fill={first.winner.fill_rate:.2f}"
    )
    print(
        f"broken winner={second.winner.tier} attempts={len(second.attempts)} "
        f"fill={second.winner.fill_rate:.2f}"
    )
    if first.winner.tier != "css" or len(first.attempts) != 1:
        return 1
    if second.winner.tier != "llm" or len(second.attempts) != 2:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
