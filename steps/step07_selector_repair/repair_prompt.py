"""Ask for one CSS selector per field. Empty means the field was not found."""

from __future__ import annotations

from pydantic import BaseModel

REPAIR_SYSTEM_PROMPT = (
    "Each field ending in _selector must be one CSS selector. "
    "Use only tags, classes, ids, and attribute selectors. "
    "The selector must match the element whose text is that field. "
    "Use an empty string when you cannot find a field. "
    "Do not put the product text in the selector."
)


class SelectorProposal(BaseModel):
    title_selector: str = ""
    price_selector: str = ""
    currency_selector: str = ""
    availability_selector: str = ""
    rating_selector: str = ""
    review_count_selector: str = ""
    brand_selector: str = ""
    sku_selector: str = ""


def proposal_selectors(parsed: SelectorProposal) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in parsed.model_dump().items():
        if not isinstance(value, str) or not value.strip():
            continue
        found[key.removesuffix("_selector")] = value.strip()
    return found


def propose(api_key: str, html: str, model: str = "gpt-4o-mini") -> dict[str, str]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    field_list = "title, price, currency, availability, rating, review_count, brand, sku"
    user = f"Return CSS selectors for: {field_list}\n\nHTML:\n{html[:20000]}"
    completion = client.beta.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        response_format=SelectorProposal,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("model returned no selectors")
    return proposal_selectors(parsed)
