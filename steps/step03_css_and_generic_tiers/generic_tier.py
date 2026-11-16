"""Tier 3. generic-extractor JSON, used when our selectors miss."""

from __future__ import annotations

import re
from typing import Any


def product_from_generic(data: dict[str, Any]) -> dict[str, str]:
    found: dict[str, str] = {}
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        found["title"] = title.strip()
    headings = data.get("headings")
    if "title" not in found and isinstance(headings, list):
        for item in headings:
            if isinstance(item, str) and item.strip():
                found["title"] = item.strip()
                break
    blob = " ".join(str(data.get(key) or "") for key in ("main_content", "description", "title"))
    match = re.search(r"[$£€]\s?\d[\d,]*(?:\.\d{2})?", blob)
    if match:
        found["price"] = re.sub(r"\s+", "", match.group(0))
    return found
