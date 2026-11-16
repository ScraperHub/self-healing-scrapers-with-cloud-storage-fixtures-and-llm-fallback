"""Tier 4: LLM extraction over readability Markdown. Fallback, not the default."""

from __future__ import annotations

from typing import Protocol

from selfheal.extractors.page import Page
from selfheal.schema import ProductSchema, Result, failed_result, success_result

SYSTEM_PROMPT = (
    "Extract one product from the markdown. "
    "Leave a field as an empty string when the page does not state it. "
    "Do not invent a price, rating, or review count."
)


class ProductModel(Protocol):
    def extract_product(self, markdown: str) -> ProductSchema:
        """Return a product parsed from markdown."""


class LlmTier:
    tier = "llm"

    def __init__(self, client: ProductModel) -> None:
        self._client = client

    def extract(self, page: Page) -> Result:
        if not page.markdown.strip():
            return failed_result(self.tier, "markdown is empty")
        try:
            product = self._client.extract_product(page.markdown)
        except Exception as exc:
            return failed_result(self.tier, f"llm extraction failed: {exc}")
        if not product.title.strip():
            return failed_result(self.tier, "model returned an empty title")
        return success_result(self.tier, product)
