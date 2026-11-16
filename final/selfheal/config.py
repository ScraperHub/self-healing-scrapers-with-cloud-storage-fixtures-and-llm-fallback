"""Load API keys from the environment or a .env file. Never hardcode them."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REQUIRED = ("CRAWLBASE_TOKEN", "CRAWLBASE_JS_TOKEN", "OPENAI_API_KEY")


def candidate_env_files(start: Path | None = None) -> list[Path]:
    origin = start or Path.cwd()
    found: list[Path] = []
    for parent in [origin, *origin.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            found.append(candidate)
    return found


def load_env(start: Path | None = None) -> None:
    for path in candidate_env_files(start):
        load_dotenv(path, override=False)


@dataclass(frozen=True)
class Settings:
    crawlbase_token: str
    crawlbase_js_token: str
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"


def load_settings(start: Path | None = None) -> Settings:
    load_env(start)
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing environment variables: {joined}")
    return Settings(
        crawlbase_token=os.environ["CRAWLBASE_TOKEN"],
        crawlbase_js_token=os.environ["CRAWLBASE_JS_TOKEN"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    )
