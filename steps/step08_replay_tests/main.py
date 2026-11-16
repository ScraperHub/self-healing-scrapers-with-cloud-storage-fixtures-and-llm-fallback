"""Replay the mirrored pages. Pass --live to store example.com and read it back."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from storage_fetch import fetch_rid, store_page
from test_replay import replay_titles

HERE = Path(__file__).resolve().parent


def main() -> int:
    titles = replay_titles()
    print("replay " + ", ".join(titles))
    if "--live" not in sys.argv:
        return 0
    _load_env()
    token = os.environ.get("CRAWLBASE_TOKEN", "")
    if not token:
        print("CRAWLBASE_TOKEN is missing")
        return 1
    rid = store_page(token, "https://example.com")
    body = fetch_rid(token, rid)
    print(f"stored rid={rid} bytes={len(body)}")
    if "Example Domain" not in body:
        return 1
    return 0


def _load_env() -> None:
    from dotenv import load_dotenv

    code = HERE.parents[1]
    load_dotenv(code / ".env")
    load_dotenv(code / "final" / ".env")


if __name__ == "__main__":
    raise SystemExit(main())
