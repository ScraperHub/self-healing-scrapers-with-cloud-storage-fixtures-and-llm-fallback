"""Seed a week of healthy CSS fills, then one empty day, and print the alert."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from drift import DriftDetector
from stats_store import Sample, StatsStore

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def main() -> int:
    store = StatsStore()
    for days_ago in (6, 4, 2):
        moment = NOW - timedelta(days=days_ago)
        _record(store, moment, "css", filled=True)
        _record(store, moment, "llm", filled=True)
    _record(store, NOW - timedelta(hours=2), "css", filled=False)
    _record(store, NOW - timedelta(hours=2), "llm", filled=True)
    # A blocked fetch must not move the baseline.
    store.record(Sample(NOW - timedelta(days=3), "allbirds", "css", "title", False, 503, 200))
    incident = DriftDetector(store).evaluate("allbirds", "title", "css", "llm", NOW)
    if incident is None:
        print("no incident")
        return 1
    print(incident.format_alert())
    return 0


def _record(store: StatsStore, moment: datetime, tier: str, filled: bool) -> None:
    store.record(Sample(moment, "allbirds", tier, "title", filled, 200, 200))


if __name__ == "__main__":
    raise SystemExit(main())
