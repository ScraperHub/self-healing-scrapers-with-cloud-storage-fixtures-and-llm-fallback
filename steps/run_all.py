"""Run every step. --live adds the network steps."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = (
    "step01_schema_and_protocol",
    "step02_crawlbase_tier",
    "step03_css_and_generic_tiers",
    "step04_llm_tier",
    "step05_tier_chain",
    "step06_drift_detection",
    "step07_selector_repair",
    "step08_replay_tests",
)
LIVE = {
    "step02_crawlbase_tier",
    "step04_llm_tier",
    "step07_selector_repair",
    "step08_replay_tests",
}


def main() -> int:
    live = "--live" in sys.argv
    for name in STEPS:
        command = [sys.executable, "main.py"]
        if live and name in LIVE:
            command.append("--live")
        print(f"run {name}", flush=True)
        result = subprocess.run(command, cwd=ROOT / name, check=False)
        if result.returncode != 0:
            print(f"failed {name} exit={result.returncode}")
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
