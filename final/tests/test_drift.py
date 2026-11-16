from __future__ import annotations

from datetime import UTC, datetime, timedelta

from selfheal.drift import DriftDetector, Sample, StatsStore, is_fetch_success

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _seed(
    store: StatsStore,
    *,
    tier: str,
    field: str,
    filled: bool,
    when: datetime,
    original_status: int | None = 200,
    cb_status: int | None = 200,
    repeats: int = 1,
) -> None:
    for index in range(repeats):
        store.record(
            Sample(
                recorded_at=when + timedelta(minutes=index),
                site="allbirds",
                url="https://www.allbirds.com/products/mens-tree-runners",
                tier=tier,
                field=field,
                filled=filled,
                original_status=original_status,
                cb_status=cb_status,
            )
        )


def _history(store: StatsStore, tier: str, field: str, filled: bool) -> None:
    for days_ago in (6, 5, 4, 3, 2):
        _seed(store, tier=tier, field=field, filled=filled, when=NOW - timedelta(days=days_ago))


def test_fetch_success_requires_both_statuses() -> None:
    assert is_fetch_success(200, 200) is True
    assert is_fetch_success(200, 503) is False
    assert is_fetch_success(404, 200) is False
    assert is_fetch_success(None, 200) is False


def test_selector_drift_when_css_drops_and_llm_holds() -> None:
    store = StatsStore()
    _history(store, "css", "price", True)
    _history(store, "llm", "price", True)
    _seed(store, tier="css", field="price", filled=False, when=NOW - timedelta(hours=2), repeats=5)
    _seed(store, tier="llm", field="price", filled=True, when=NOW - timedelta(hours=2), repeats=5)
    incidents = DriftDetector(store).evaluate("allbirds", ["price"], "css", "llm", now=NOW)
    assert len(incidents) == 1
    assert incidents[0].drop > 0.30
    assert "selector drift" in incidents[0].format_alert()
    store.close()


def test_exact_threshold_is_not_an_incident() -> None:
    store = StatsStore()
    _history(store, "css", "price", True)
    _history(store, "llm", "price", True)
    # 7 of 10 filled is a 0.30 drop from a 1.0 baseline.
    for index in range(10):
        _seed(
            store,
            tier="css",
            field="price",
            filled=index < 7,
            when=NOW - timedelta(hours=3, minutes=index),
        )
    _seed(store, tier="llm", field="price", filled=True, when=NOW - timedelta(hours=2), repeats=4)
    incidents = DriftDetector(store).evaluate("allbirds", ["price"], "css", "llm", now=NOW)
    assert incidents == []
    store.close()


def test_no_incident_when_the_confirming_tier_also_drops() -> None:
    store = StatsStore()
    _history(store, "css", "title", True)
    _history(store, "llm", "title", True)
    _seed(store, tier="css", field="title", filled=False, when=NOW - timedelta(hours=1), repeats=4)
    _seed(store, tier="llm", field="title", filled=False, when=NOW - timedelta(hours=1), repeats=4)
    incidents = DriftDetector(store).evaluate("allbirds", ["title"], "css", "llm", now=NOW)
    assert incidents == []
    store.close()


def test_fetch_failures_are_ignored() -> None:
    store = StatsStore()
    _history(store, "css", "title", True)
    _history(store, "llm", "title", True)
    _seed(
        store,
        tier="css",
        field="title",
        filled=False,
        when=NOW - timedelta(hours=1),
        original_status=503,
        cb_status=503,
        repeats=4,
    )
    incidents = DriftDetector(store).evaluate("allbirds", ["title"], "css", "llm", now=NOW)
    assert incidents == []
    store.close()


def test_short_baseline_does_not_alert() -> None:
    store = StatsStore()
    _seed(store, tier="css", field="title", filled=True, when=NOW - timedelta(days=3), repeats=2)
    _seed(store, tier="llm", field="title", filled=True, when=NOW - timedelta(days=3))
    _seed(store, tier="css", field="title", filled=False, when=NOW - timedelta(hours=1))
    _seed(store, tier="llm", field="title", filled=True, when=NOW - timedelta(hours=1))
    incidents = DriftDetector(store).evaluate("allbirds", ["title"], "css", "llm", now=NOW)
    assert incidents == []
    store.close()


def test_samples_older_than_the_window_are_ignored() -> None:
    store = StatsStore()
    _seed(store, tier="css", field="title", filled=True, when=NOW - timedelta(days=12), repeats=5)
    _seed(store, tier="llm", field="title", filled=True, when=NOW - timedelta(days=12), repeats=5)
    _seed(store, tier="css", field="title", filled=False, when=NOW - timedelta(hours=1), repeats=3)
    _seed(store, tier="llm", field="title", filled=True, when=NOW - timedelta(hours=1), repeats=3)
    incidents = DriftDetector(store).evaluate("allbirds", ["title"], "css", "llm", now=NOW)
    assert incidents == []
    store.close()
