"""Create .env files from keys.md. Does not print secret values."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
text = (ROOT / "keys.md").read_text(encoding="utf-8")
keys = re.findall(r"`([^`]+)`", text)
if len(keys) != 3:
    raise SystemExit(f"expected 3 secrets, found {len(keys)}")
body = (
    f"CRAWLBASE_TOKEN={keys[0]}\n"
    f"CRAWLBASE_JS_TOKEN={keys[1]}\n"
    f"OPENAI_API_KEY={keys[2]}\n"
    "OPENAI_MODEL=gpt-4o-mini\n"
)
for relative in (Path("code/.env"), Path("code/final/.env")):
    (ROOT / relative).write_text(body, encoding="utf-8")
print("wrote env files")
