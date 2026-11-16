"""Tier 4. Structured output over Markdown. Empty strings mean missing."""

from __future__ import annotations

import re
from typing import Protocol

from pydantic import BaseModel


class LlmProduct(BaseModel):
    title: str
    price: str = ""
    currency: str = ""
    availability: str = ""
    rating: str = ""
    review_count: str = ""
    brand: str = ""
    sku: str = ""


class ProductModel(Protocol):
    def parse(self, markdown: str) -> LlmProduct:
        """Return the product described by this Markdown."""


SYSTEM_PROMPT = (
    "Extract one product from the Markdown. "
    "Use an empty string for any field you cannot see. "
    "Copy the price with its currency symbol."
)


class OpenAiModel:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    def parse(self, markdown: str) -> LlmProduct:
        completion = self._client.beta.chat.completions.parse(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": markdown[:30000]},
            ],
            response_format=LlmProduct,
        )
        usage = completion.usage
        if usage is not None:
            self.last_input_tokens = int(usage.prompt_tokens or 0)
            self.last_output_tokens = int(usage.completion_tokens or 0)
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("model returned no product")
        return parsed


class LlmTier:
    def __init__(self, model: ProductModel) -> None:
        self.model = model
        self.tier = "llm"

    def extract(self, markdown: str) -> LlmProduct:
        if not markdown.strip():
            raise ValueError("markdown is empty")
        parsed = self.model.parse(markdown)
        if not parsed.title.strip():
            raise ValueError("model returned no title")
        return parsed


def fill_rate(product: LlmProduct) -> float:
    values = (
        product.title,
        product.price,
        product.currency or _currency(product.price),
        product.availability,
        product.rating,
        product.review_count,
        product.brand,
        product.sku,
    )
    filled = sum(1 for value in values if value.strip())
    return filled / len(values)


def _currency(price: str) -> str:
    if "$" in price:
        return "USD"
    if "£" in price:
        return "GBP"
    if "€" in price:
        return "EUR"
    return ""


class ScriptedModel:
    def parse(self, markdown: str) -> LlmProduct:
        return scripted_parse(markdown)


def scripted_parse(markdown: str) -> LlmProduct:
    """Offline stand-in. The live path uses OpenAiModel.parse instead."""

    def line_after(label: str) -> str:
        match = re.search(rf"{label}:\s*(.+)", markdown)
        return match.group(1).strip() if match else ""

    title = ""
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    price = line_after("Price")
    return LlmProduct(
        title=title,
        price=price,
        currency=_currency(price),
        availability=line_after("Availability"),
        brand=line_after("Brand"),
        sku=line_after("SKU"),
    )
