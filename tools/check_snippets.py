"""Every blog code fence that names a step file must appear in that file, in order."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOG = ROOT.parent / "draft" / "self-healing-scrapers-with-cloud-storage-fixtures-and-llm-fallback.md"
FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\n(.*?)```", re.DOTALL)
FROM = re.compile(r"^# From steps/(\S+)\s*$")


def main() -> int:
    text = BLOG.read_text(encoding="utf-8")
    failures: list[str] = []
    checked = 0
    for block in FENCE.findall(text):
        lines = block.splitlines()
        if not lines:
            continue
        match = FROM.match(lines[0].strip())
        if match is None:
            failures.append("code fence is missing a # From steps/... line")
            continue
        relative = match.group(1)
        path = ROOT / "steps" / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
            continue
        source = path.read_text(encoding="utf-8").splitlines()
        wanted = [line for line in lines[1:] if line.strip()]
        if not _in_order(source, wanted):
            failures.append(f"snippet not found in {relative}")
            continue
        checked += 1
    if failures:
        print(f"checked {checked}")
        for item in failures:
            print(" -", item)
        return 1
    print(f"checked {checked} snippets")
    return 0


def _in_order(source: list[str], wanted: list[str]) -> bool:
    cursor = 0
    for line in wanted:
        found = False
        while cursor < len(source):
            if source[cursor].strip() == line.strip():
                found = True
                cursor += 1
                break
            cursor += 1
        if not found:
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
