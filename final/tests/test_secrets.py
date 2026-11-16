"""Fail if a real key from keys.md is copied into the project."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
SKIP = {".venv", ".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "repair_out"}


def _secrets() -> list[str]:
    text = (ROOT / "keys.md").read_text(encoding="utf-8")
    return [item for item in re.findall(r"`([^`]{12,})`", text)]


def test_keys_md_exists_and_source_does_not_repeat_it() -> None:
    secrets = _secrets()
    assert len(secrets) >= 3
    leaks: list[str] = []
    for path in CODE.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if path.name == ".env":
            continue
        if path.suffix.lower() not in {
            ".py",
            ".md",
            ".json",
            ".toml",
            ".svg",
            ".html",
            ".txt",
            ".example",
        }:
            if path.name not in {".env.example", ".gitignore"}:
                continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for secret in secrets:
            if secret in text:
                leaks.append(str(path.relative_to(ROOT)))
                break
    assert leaks == []
