"""Validate a proposal on two snapshots and write a diff. --live asks the model."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from diff_output import selectors_diff, write_diff
from repair_prompt import propose
from validator import validate_selectors

HERE = Path(__file__).resolve().parent

BROKEN = {"title": "h1.missing", "price": ".missing"}
KNOWN_GOOD = {"title": "h1.product-title", "price": "span.product-price"}


def main() -> int:
    html = (HERE / "sample.html").read_text(encoding="utf-8")
    snapshots = [html, html.replace("Tree Runner", "Wool Runner")]
    if "--live" in sys.argv:
        _load_env()
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            print("OPENAI_API_KEY is missing")
            return 1
        proposed = propose(key, html, os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    else:
        proposed = dict(KNOWN_GOOD)
    report = validate_selectors(proposed, snapshots)
    diff = selectors_diff(BROKEN, proposed, "selectors/allbirds.json")
    destination = HERE / "repair_out" / "allbirds.diff"
    write_diff(diff, destination)
    print(f"ok={report.ok} diff={destination.name} bytes={len(diff)}")
    if not report.ok:
        print("failures " + ", ".join(report.failures))
        print("selectors " + json.dumps(proposed, sort_keys=True))
        return 1
    if "product-title" not in diff and "--live" not in sys.argv:
        return 1
    return 0


def _load_env() -> None:
    from dotenv import load_dotenv

    code = HERE.parents[1]
    load_dotenv(code / ".env")
    load_dotenv(code / "final" / ".env")


if __name__ == "__main__":
    raise SystemExit(main())
