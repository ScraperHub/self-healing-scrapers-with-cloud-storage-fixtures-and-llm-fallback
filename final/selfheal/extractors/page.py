"""Shared page object passed to every extractor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Page:
    url: str
    site: str = ""
    html: str = ""
    markdown: str = ""
    scraper_json: dict[str, Any] | None = None
    generic_json: dict[str, Any] | None = None
    original_status: int | None = None
    cb_status: int | None = None
    rid: str | None = None
    extras: dict[str, str] = field(default_factory=dict)
