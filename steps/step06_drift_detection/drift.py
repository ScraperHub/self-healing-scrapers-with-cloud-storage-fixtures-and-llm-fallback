"""An incident is a watch-tier drop of more than 30 points while the LLM tier holds."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from stats_store import StatsStore

DROP_POINTS = 30
CONFIRM_TOLERANCE_POINTS = 10
MIN_BASELINE_SAMPLES = 3


@dataclass(frozen=True)
class DriftIncident:
    site: str
    field: str
    watch_tier: str
    confirm_tier: str
    baseline_fill_rate: float
    current_fill_rate: float
    confirm_current: float

    def format_alert(self) -> str:
        drop_points = round((self.baseline_fill_rate - self.current_fill_rate) * 100)
        return (
            f"selector drift on {self.site}.{self.field}: "
            f"{self.watch_tier} fill rate {self.current_fill_rate:.0%} "
            f"vs baseline {self.baseline_fill_rate:.0%} ({drop_points} points). "
            f"{self.confirm_tier} stayed at {self.confirm_current:.0%}."
        )


class DriftDetector:
    def __init__(self, store: StatsStore) -> None:
        self.store = store

    def evaluate(
        self,
        site: str,
        field: str,
        watch_tier: str,
        confirm_tier: str,
        now: datetime,
    ) -> DriftIncident | None:
        current_start = now - timedelta(days=1)
        baseline_start = now - timedelta(days=7)
        baseline, baseline_n = self.store.mean_fill(
            site=site, tier=watch_tier, field=field, start=baseline_start, end=current_start
        )
        current, current_n = self.store.mean_fill(
            site=site, tier=watch_tier, field=field, start=current_start, end=now
        )
        confirm_base, confirm_base_n = self.store.mean_fill(
            site=site, tier=confirm_tier, field=field, start=baseline_start, end=current_start
        )
        confirm_now, confirm_now_n = self.store.mean_fill(
            site=site, tier=confirm_tier, field=field, start=current_start, end=now
        )
        if (
            baseline is None
            or current is None
            or confirm_base is None
            or confirm_now is None
            or baseline_n < MIN_BASELINE_SAMPLES
            or current_n < 1
            or confirm_base_n < 1
            or confirm_now_n < 1
        ):
            return None
        drop_points = round((baseline - current) * 100)
        confirm_drop = round((confirm_base - confirm_now) * 100)
        if drop_points <= DROP_POINTS or confirm_drop > CONFIRM_TOLERANCE_POINTS:
            return None
        return DriftIncident(
            site=site,
            field=field,
            watch_tier=watch_tier,
            confirm_tier=confirm_tier,
            baseline_fill_rate=baseline,
            current_fill_rate=current,
            confirm_current=confirm_now,
        )
