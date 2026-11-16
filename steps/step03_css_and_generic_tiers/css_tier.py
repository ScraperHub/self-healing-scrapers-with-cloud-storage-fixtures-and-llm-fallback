"""Tier 2. CSS selectors over a saved page."""

from __future__ import annotations

import json
import re
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser as HTMLParser


def load_selectors(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(value, str)}


def apply_selectors(html: str, selectors: dict[str, str]) -> dict[str, str]:
    tree = HTMLParser(html)
    found: dict[str, str] = {}
    for field, selector in selectors.items():
        node = tree.css_first(selector)
        if node is None:
            continue
        text = (node.text(strip=True) or "").strip()
        if not text:
            content = node.attributes.get("content")
            text = content.strip() if isinstance(content, str) else ""
        if not text:
            text = _attribute_text(node, selector)
        if text:
            found[field] = text
    return found


def _attribute_text(node: object, selector: str) -> str:
    match = re.search(r"\[([^\]=\s]+)", selector)
    if match is None:
        return ""
    attributes = getattr(node, "attributes", {})
    value = attributes.get(match.group(1)) if isinstance(attributes, dict) else None
    return value.strip() if isinstance(value, str) else ""
