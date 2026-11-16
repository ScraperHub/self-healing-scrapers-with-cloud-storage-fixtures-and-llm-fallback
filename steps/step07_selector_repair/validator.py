"""Accept selectors only when every snapshot fills the required fields."""

from __future__ import annotations

from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import SelectolaxError


@dataclass
class ValidationReport:
    ok: bool
    failures: list[str]


def validate_selectors(
    selectors: dict[str, str],
    snapshots: list[str],
    required: tuple[str, ...] = ("title", "price"),
) -> ValidationReport:
    if not snapshots:
        return ValidationReport(False, ["no snapshots"])
    failures: list[str] = []
    for index, html in enumerate(snapshots, start=1):
        found = _apply(html, selectors)
        for field in required:
            if not found.get(field, "").strip():
                failures.append(f"snapshot {index} missed {field}")
    return ValidationReport(ok=not failures, failures=failures)


def _apply(html: str, selectors: dict[str, str]) -> dict[str, str]:
    tree = HTMLParser(html)
    found: dict[str, str] = {}
    for field, selector in selectors.items():
        if not selector:
            continue
        node = None
        try:
            node = tree.css_first(selector)
        except SelectolaxError:
            node = None
        if node is None:
            continue
        text = (node.text(strip=True) or "").strip()
        if text:
            found[field] = text
    return found
