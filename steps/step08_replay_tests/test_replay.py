"""Replay mirrored HTML with no network."""

from __future__ import annotations

import json
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser as HTMLParser

HERE = Path(__file__).resolve().parent
SELECTORS = {"title": "h1.product-title", "price": "span.product-price"}


def replay_titles() -> list[str]:
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    titles: list[str] = []
    for item in manifest["fixtures"]:
        html = (HERE / item["html"]).read_text(encoding="utf-8")
        found = _apply(html)
        if not found.get("title") or not found.get("price"):
            raise AssertionError(f"{item['rid']} did not fill title and price")
        titles.append(found["title"])
    return titles


def test_replay_fills_title_and_price() -> None:
    titles = replay_titles()
    assert titles == ["Men's Tree Runner", "Men's Wool Runner"]


def _apply(html: str) -> dict[str, str]:
    tree = HTMLParser(html)
    found: dict[str, str] = {}
    for field, selector in SELECTORS.items():
        node = tree.css_first(selector)
        if node is None:
            continue
        text = (node.text(strip=True) or "").strip()
        if text:
            found[field] = text
    return found
