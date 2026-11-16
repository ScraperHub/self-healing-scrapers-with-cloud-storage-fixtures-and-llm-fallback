"""OpenAI structured-output calls for extraction and selector repair."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from selfheal.extractors.llm_tier import SYSTEM_PROMPT
from selfheal.schema import ProductSchema, as_float, as_int, currency_from_price, price_text


class LlmProduct(BaseModel):
    """All strings, so the JSON schema has no nulls. Empty means missing."""

    title: str
    price: str = ""
    currency: str = ""
    availability: str = ""
    rating: str = ""
    review_count: str = ""
    brand: str = ""
    sku: str = ""


class SelectorProposalModel(BaseModel):
    title: str
    price: str
    currency: str = ""
    availability: str = ""
    rating: str = ""
    review_count: str = ""
    brand: str = ""
    sku: str = ""
    notes: str = ""


def to_product(parsed: LlmProduct) -> ProductSchema:
    price = price_text(parsed.price) or (parsed.price.strip() or None)
    return ProductSchema(
        title=parsed.title.strip(),
        price=price,
        currency=currency_from_price(price, parsed.currency or None),
        availability=parsed.availability.strip() or None,
        rating=as_float(parsed.rating),
        review_count=as_int(parsed.review_count),
        brand=parsed.brand.strip() or None,
        sku=parsed.sku.strip() or None,
    )


def proposal_selectors(parsed: SelectorProposalModel) -> dict[str, str]:
    raw = parsed.model_dump()
    raw.pop("notes", None)
    return {
        key: value.strip() for key, value in raw.items() if isinstance(value, str) and value.strip()
    }


REPAIR_SYSTEM_PROMPT = (
    "Propose one CSS selector per product field. "
    "The selector must match the element whose text is the value. "
    "Use an empty string when you cannot find a field. "
    "Do not explain the selectors in the field values."
)


ModelT = TypeVar("ModelT", LlmProduct, SelectorProposalModel)


class OpenAiClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    def extract_product(self, markdown: str) -> ProductSchema:
        parsed = self._parse(SYSTEM_PROMPT, markdown[:30000], LlmProduct)
        return to_product(parsed)

    def propose_selectors(self, html: str, fields: list[str]) -> dict[str, str]:
        field_list = ", ".join(fields)
        user = f"Fields: {field_list}\n\nHTML:\n{html[:20000]}"
        parsed = self._parse(REPAIR_SYSTEM_PROMPT, user, SelectorProposalModel)
        return proposal_selectors(parsed)

    def _parse(self, system: str, user: str, model: type[ModelT]) -> ModelT:
        completion = self._client.beta.chat.completions.parse(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=model,
        )
        usage = completion.usage
        if usage is not None:
            self.last_input_tokens = int(usage.prompt_tokens or 0)
            self.last_output_tokens = int(usage.completion_tokens or 0)
        choice = completion.choices[0].message
        if choice.parsed is None:
            refusal = getattr(choice, "refusal", None) or "empty parse"
            raise RuntimeError(f"model refused or returned nothing: {refusal}")
        return choice.parsed
