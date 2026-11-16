"""Load the mirrored fixture library."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from selfheal.extractors.page import Page


@dataclass(frozen=True)
class Fixture:
    rid: str
    site: str
    url: str
    html: str
    scraper_json: str | None = None
    generic_json: str | None = None
    markdown: str | None = None
    original_status: int | None = 200
    cb_status: int | None = 200


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _opt_int(value: object, default: int) -> int | None:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, int):
        return value
    return default


def load_manifest(path: Path) -> list[Fixture]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("fixtures", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a fixture list")
    fixtures: list[Fixture] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        html = _opt_str(row.get("html"))
        rid = _opt_str(row.get("rid"))
        site = _opt_str(row.get("site"))
        url = _opt_str(row.get("url"))
        if not html or not rid or not site or not url:
            continue
        fixtures.append(
            Fixture(
                rid=rid,
                site=site,
                url=url,
                html=html,
                scraper_json=_opt_str(row.get("scraper_json")),
                generic_json=_opt_str(row.get("generic_json")),
                markdown=_opt_str(row.get("markdown")),
                original_status=_opt_int(row.get("original_status"), 200),
                cb_status=_opt_int(row.get("cb_status"), 200),
            )
        )
    return fixtures


def _read(root: Path, relative: str | None) -> str:
    if not relative:
        return ""
    path = root / relative
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(root: Path, relative: str | None) -> dict[str, Any] | None:
    text = _read(root, relative)
    if not text:
        return None
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        return parsed
    return None


def load_page(root: Path, fixture: Fixture) -> Page:
    return Page(
        url=fixture.url,
        site=fixture.site,
        html=_read(root, fixture.html),
        markdown=_read(root, fixture.markdown),
        scraper_json=_read_json(root, fixture.scraper_json),
        generic_json=_read_json(root, fixture.generic_json),
        original_status=fixture.original_status,
        cb_status=fixture.cb_status,
        rid=fixture.rid,
    )
