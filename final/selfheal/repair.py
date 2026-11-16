"""Propose CSS selectors and accept them only when stored snapshots agree."""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from selfheal.extractors.css_tier import apply_selectors
from selfheal.schema import ProductSchema

MAX_HTML_CHARS = 20000


def slim_html(html: str) -> str:
    tree = HTMLParser(html)
    for node in tree.css("script, style, noscript, svg, iframe"):
        node.decompose()
    return tree.html or html


def clean_html(html: str, limit: int = MAX_HTML_CHARS) -> str:
    tree = HTMLParser(html)
    for node in tree.css("script, style, noscript, svg"):
        node.decompose()
    rendered = tree.html or ""
    return rendered[:limit]


@dataclass
class ValidationReport:
    ok: bool
    failures: list[str]
    extracted: list[dict[str, str]]

    def summary(self) -> str:
        if self.ok:
            return f"passed on {len(self.extracted)} snapshots"
        return "failed: " + " | ".join(self.failures)


def validate_selectors(
    selectors: dict[str, str],
    snapshots: list[str],
    required: tuple[str, ...] = ("title", "price"),
    reference: ProductSchema | None = None,
    agree_fields: tuple[str, ...] = ("title",),
) -> ValidationReport:
    if not snapshots:
        return ValidationReport(False, ["no snapshots"], [])
    failures: list[str] = []
    extracted: list[dict[str, str]] = []
    for index, html in enumerate(snapshots, start=1):
        found = apply_selectors(html, selectors)
        extracted.append(found)
        for field in required:
            if not found.get(field, "").strip():
                failures.append(f"snapshot {index} missed {field}")
        if reference is not None and index == len(snapshots):
            if not _agrees(found, reference, agree_fields):
                failures.append(f"snapshot {index} disagrees with the llm values")
    return ValidationReport(ok=not failures, failures=failures, extracted=extracted)


def _agrees(found: dict[str, str], reference: ProductSchema, fields: tuple[str, ...]) -> bool:
    for field in fields:
        expected = str(getattr(reference, field) or "").strip().casefold()
        got = found.get(field, "").strip().casefold()
        if not expected:
            continue
        if expected not in got and got not in expected:
            return False
    return True


def selectors_diff(before: dict[str, str], after: dict[str, str], path: str) -> str:
    old = json.dumps(before, indent=2, sort_keys=True) + "\n"
    new = json.dumps(after, indent=2, sort_keys=True) + "\n"
    lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(lines)


def write_diff(diff: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(diff, encoding="utf-8")
    return destination


def break_selector_targets(html: str, selectors: dict[str, str], suffix: str = "-shifted") -> str:
    """Rename class tokens so the current selectors miss. Used by the drift simulation."""

    mutated = html
    for selector in selectors.values():
        for token in _class_tokens(selector):
            mutated = mutated.replace(token, token + suffix)
    return mutated


def shifted_selectors(selectors: dict[str, str], suffix: str = "-shifted") -> dict[str, str]:
    updated: dict[str, str] = {}
    for field, selector in selectors.items():
        text = selector
        for token in _class_tokens(selector):
            text = text.replace(token, token + suffix)
        updated[field] = text
    return updated


_CLASS = re.compile(r"\.([A-Za-z_][\w-]*)")


def _class_tokens(selector: str) -> list[str]:
    found: list[str] = []
    for name in _CLASS.findall(selector):
        if name not in found:
            found.append(name)
    return found
