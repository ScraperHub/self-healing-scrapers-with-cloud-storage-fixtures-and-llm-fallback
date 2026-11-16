"""Tier 2: CSS selectors over stored HTML."""

from __future__ import annotations

import json
import re
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from selfheal.extractors.mapping import product_from_mapping
from selfheal.extractors.page import Page
from selfheal.schema import Result, failed_result, success_result

PACKAGE_SELECTORS = Path(__file__).resolve().parent.parent / "selectors"


def load_selectors(site: str, directory: Path | None = None) -> dict[str, str]:
    root = directory or PACKAGE_SELECTORS
    path = root / f"{site}.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(value, str)}


def apply_selectors(html: str, selectors: dict[str, str]) -> dict[str, str]:
    tree = HTMLParser(html)
    found: dict[str, str] = {}
    for field, selector in selectors.items():
        if not selector:
            continue
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
    value = attributes.get(match.group(1))
    return value.strip() if isinstance(value, str) else ""


class CssTier:
    tier = "css"

    def __init__(
        self, selectors: dict[str, str] | None = None, directory: Path | None = None
    ) -> None:
        self._selectors = selectors
        self._directory = directory

    def selectors_for(self, page: Page) -> dict[str, str]:
        if self._selectors is not None:
            return self._selectors
        return load_selectors(page.site, self._directory)

    def extract(self, page: Page) -> Result:
        if not page.html.strip():
            return failed_result(self.tier, "html is empty")
        selectors = self.selectors_for(page)
        if not selectors:
            return failed_result(self.tier, f"no selectors for {page.site or 'page'}")
        try:
            found = apply_selectors(page.html, selectors)
        except Exception as exc:
            return failed_result(self.tier, f"css parse failed: {exc}")
        product = product_from_mapping(found)
        if product is None:
            return failed_result(self.tier, "selectors missed the title")
        return success_result(self.tier, product)
