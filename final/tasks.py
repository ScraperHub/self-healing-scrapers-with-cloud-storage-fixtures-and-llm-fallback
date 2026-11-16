"""Cross-platform tasks. Run from code/final: python tasks.py test"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CODE = ROOT.parent


def _run(args: list[str], cwd: Path | None = None) -> int:
    print("+", " ".join(args))
    completed = subprocess.run(args, cwd=cwd or ROOT)
    return completed.returncode


def test() -> int:
    return _run([sys.executable, "-m", "pytest", "-m", "not live"])


def test_live() -> int:
    return _run([sys.executable, "-m", "pytest", "-m", "live"])


def lint() -> int:
    code = _run([sys.executable, "-m", "ruff", "check", "."])
    if code != 0:
        return code
    return _run([sys.executable, "-m", "ruff", "format", "--check", "."])


def typecheck() -> int:
    return _run([sys.executable, "-m", "mypy"])


def coverage() -> int:
    return _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "not live",
            "--cov=selfheal",
            "--cov-report=term-missing",
        ]
    )


def verify_assumptions() -> int:
    return _run([sys.executable, "scripts/verify_assumptions.py"])


def refresh_fixtures() -> int:
    return _run([sys.executable, "scripts/refresh_fixtures.py"])


def steps() -> int:
    return _run([sys.executable, "steps/run_all.py"], cwd=CODE)


TASKS = {
    "test": test,
    "test-live": test_live,
    "lint": lint,
    "typecheck": typecheck,
    "coverage": coverage,
    "verify-assumptions": verify_assumptions,
    "refresh-fixtures": refresh_fixtures,
    "steps": steps,
}


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    task = TASKS.get(name)
    if task is None:
        known = ", ".join(sorted(TASKS))
        print(f"Usage: python tasks.py <task>\nTasks: {known}")
        return 2
    return task()


if __name__ == "__main__":
    raise SystemExit(main())
