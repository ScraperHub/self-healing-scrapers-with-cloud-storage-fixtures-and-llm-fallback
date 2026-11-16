"""Map a saved scraper payload. Pass --live to store one page and print its rid."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from crawlbase_tier import fill_rate, product_from_scraper
from store_crawl import crawl_store

HERE = Path(__file__).resolve().parent


def main() -> int:
    payload = json.loads((HERE / "sample_amazon.json").read_text(encoding="utf-8"))
    product = product_from_scraper(payload)
    if product is None:
        print("scraper payload had no title")
        return 1
    rate = fill_rate(product)
    print(f"tier=crawlbase fill={rate:.2f} title={product.title}")
    if rate < 0.75:
        return 1
    if "--live" not in sys.argv:
        return 0
    _load_env()
    token = os.environ.get("CRAWLBASE_TOKEN", "")
    if not token:
        print("CRAWLBASE_TOKEN is missing")
        return 1
    rid = crawl_store(token, "https://example.com")
    print(f"stored rid={rid}")
    return 0 if rid else 1


def _load_env() -> None:
    from dotenv import load_dotenv

    code = HERE.parents[1]
    load_dotenv(code / ".env")
    load_dotenv(code / "final" / ".env")


if __name__ == "__main__":
    raise SystemExit(main())
