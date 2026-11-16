"""Tier 3: generic-extractor JSON, site agnostic and thin."""

from __future__ import annotations

import re
from typing import Any

from selfheal.extractors.mapping import product_from_mapping
from selfheal.extractors.page import Page
from selfheal.schema import Result, failed_result, success_result

_PRICE = re.compile(r"([$£€]\s?\d[\d,]*(?:\.\d{2})?)")


def _first_heading(payload: dict[str, Any]) -> str | None:
    headings = payload.get("headings")
    if not isinstance(headings, dict):
        return None
    for key in ("h1", "h2"):
        values = headings.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None


def fields_from_generic(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title") if isinstance(payload.get("title"), str) else None
    if not title:
        title = _first_heading(payload)
    content = payload.get("main_content") if isinstance(payload.get("main_content"), str) else ""
    description = payload.get("description") if isinstance(payload.get("description"), str) else ""
    blob = f"{content}\n{description}"
    price_match = _PRICE.search(blob)
    return {
        "title": title,
        "price": price_match.group(1) if price_match else None,
    }


class GenericTier:
    tier = "generic"

    def extract(self, page: Page) -> Result:
        if not page.generic_json:
            return failed_result(self.tier, "no generic extractor payload")
        product = product_from_mapping(fields_from_generic(page.generic_json))
        if product is None:
            return failed_result(self.tier, "generic extractor has no title")
        return success_result(self.tier, product)
