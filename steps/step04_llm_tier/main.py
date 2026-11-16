"""Extract the sample Markdown. Pass --live to call the configured OpenAI model."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from llm_tier import LlmTier, OpenAiModel, ScriptedModel, fill_rate

HERE = Path(__file__).resolve().parent


def main() -> int:
    markdown = (HERE / "sample_allbirds.md").read_text(encoding="utf-8")
    if "--live" in sys.argv:
        _load_env()
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            print("OPENAI_API_KEY is missing")
            return 1
        model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        live_model = OpenAiModel(key, model_name)
        product = LlmTier(live_model).extract(markdown)
        print(
            f"tier=llm fill={fill_rate(product):.2f} title={product.title} "
            f"tokens={live_model.last_input_tokens}+{live_model.last_output_tokens}"
        )
    else:
        product = LlmTier(ScriptedModel()).extract(markdown)
        print(f"tier=llm fill={fill_rate(product):.2f} title={product.title}")
    if "Tree" not in product.title or not product.price:
        return 1
    return 0


def _load_env() -> None:
    from dotenv import load_dotenv

    code = HERE.parents[1]
    load_dotenv(code / ".env")
    load_dotenv(code / "final" / ".env")


if __name__ == "__main__":
    raise SystemExit(main())
