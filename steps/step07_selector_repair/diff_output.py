"""A unified diff of selectors.json. Nothing is written back to the live file."""

from __future__ import annotations

import difflib
import json
from pathlib import Path


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
