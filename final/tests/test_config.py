from __future__ import annotations

from pathlib import Path

import pytest
from selfheal.config import REQUIRED, load_settings

FINAL = Path(__file__).resolve().parents[1]


def test_missing_env_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in REQUIRED:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("selfheal.config.candidate_env_files", lambda start=None: [])
    with pytest.raises(RuntimeError, match="Missing environment variables"):
        load_settings(tmp_path)


def test_reads_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in REQUIRED:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "CRAWLBASE_TOKEN=normal",
                "CRAWLBASE_JS_TOKEN=js",
                "OPENAI_API_KEY=sk-test",
                "OPENAI_MODEL=gpt-4o-mini",
            ]
        ),
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.crawlbase_token == "normal"
    assert settings.crawlbase_js_token == "js"
    assert settings.openai_model == "gpt-4o-mini"
    assert FINAL.name == "final"
