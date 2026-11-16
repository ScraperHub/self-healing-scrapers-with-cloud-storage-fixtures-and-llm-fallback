"""Rolling fill-rate baseline and the selector-drift rule."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

DEFAULT_DROP = 0.30
DEFAULT_LLM_TOLERANCE = 0.10
DEFAULT_BASELINE_DAYS = 7
MIN_BASELINE_SAMPLES = 3


def utcnow() -> datetime:
    return datetime.now(UTC)


def is_fetch_success(original_status: int | None, cb_status: int | None) -> bool:
    return original_status == 200 and cb_status == 200


@dataclass(frozen=True)
class Sample:
    recorded_at: datetime
    site: str
    url: str
    tier: str
    field: str
    filled: bool
    original_status: int | None
    cb_status: int | None


@dataclass(frozen=True)
class DriftIncident:
    site: str
    field: str
    watch_tier: str
    confirm_tier: str
    baseline_fill_rate: float
    current_fill_rate: float
    confirm_baseline: float
    confirm_current: float

    @property
    def drop(self) -> float:
        return self.baseline_fill_rate - self.current_fill_rate

    def format_alert(self) -> str:
        drop_points = round(self.drop * 100)
        return (
            f"selector drift on {self.site}.{self.field}: "
            f"{self.watch_tier} fill rate {self.current_fill_rate:.0%} "
            f"vs baseline {self.baseline_fill_rate:.0%} ({drop_points} points). "
            f"{self.confirm_tier} stayed at {self.confirm_current:.0%}."
        )


class StatsStore:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                recorded_at TEXT NOT NULL,
                site TEXT NOT NULL,
                url TEXT NOT NULL,
                tier TEXT NOT NULL,
                field TEXT NOT NULL,
                filled INTEGER NOT NULL,
                original_status INTEGER,
                cb_status INTEGER
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record(self, sample: Sample) -> None:
        self._conn.execute(
            """
            INSERT INTO samples (
                recorded_at, site, url, tier, field, filled, original_status, cb_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample.recorded_at.astimezone(UTC).isoformat(),
                sample.site,
                sample.url,
                sample.tier,
                sample.field,
                1 if sample.filled else 0,
                sample.original_status,
                sample.cb_status,
            ),
        )
        self._conn.commit()

    def record_fields(
        self,
        *,
        recorded_at: datetime,
        site: str,
        url: str,
        tier: str,
        field_nulls: dict[str, bool],
        original_status: int | None,
        cb_status: int | None,
    ) -> None:
        for field, is_null in field_nulls.items():
            self.record(
                Sample(
                    recorded_at=recorded_at,
                    site=site,
                    url=url,
                    tier=tier,
                    field=field,
                    filled=not is_null,
                    original_status=original_status,
                    cb_status=cb_status,
                )
            )

    def mean_fill(
        self,
        *,
        site: str,
        tier: str,
        field: str,
        start: datetime,
        end: datetime,
    ) -> tuple[float | None, int]:
        row = self._conn.execute(
            """
            SELECT AVG(filled) AS rate, COUNT(*) AS n
            FROM samples
            WHERE site = ? AND tier = ? AND field = ?
              AND recorded_at > ? AND recorded_at <= ?
              AND original_status = 200 AND cb_status = 200
            """,
            (
                site,
                tier,
                field,
                start.astimezone(UTC).isoformat(),
                end.astimezone(UTC).isoformat(),
            ),
        ).fetchone()
        count = int(row["n"] or 0)
        if count == 0 or row["rate"] is None:
            return None, 0
        return float(row["rate"]), count


class DriftDetector:
    def __init__(
        self,
        store: StatsStore,
        drop: float = DEFAULT_DROP,
        confirm_tolerance: float = DEFAULT_LLM_TOLERANCE,
        baseline_days: int = DEFAULT_BASELINE_DAYS,
        min_baseline_samples: int = MIN_BASELINE_SAMPLES,
    ) -> None:
        self.store = store
        self.drop = drop
        self.confirm_tolerance = confirm_tolerance
        self.baseline_days = baseline_days
        self.min_baseline_samples = min_baseline_samples

    def evaluate(
        self,
        site: str,
        fields: list[str],
        watch_tier: str,
        confirm_tier: str,
        now: datetime | None = None,
    ) -> list[DriftIncident]:
        moment = now or utcnow()
        current_start = moment - timedelta(days=1)
        baseline_start = moment - timedelta(days=self.baseline_days)
        incidents: list[DriftIncident] = []
        for field in fields:
            incident = self._field(
                site, field, watch_tier, confirm_tier, baseline_start, current_start, moment
            )
            if incident is not None:
                incidents.append(incident)
        return incidents

    def _field(
        self,
        site: str,
        field: str,
        watch_tier: str,
        confirm_tier: str,
        baseline_start: datetime,
        current_start: datetime,
        now: datetime,
    ) -> DriftIncident | None:
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
            or baseline_n < self.min_baseline_samples
            or current_n < 1
            or confirm_base_n < 1
            or confirm_now_n < 1
        ):
            return None
        drop = baseline - current
        # "More than X points": a drop of exactly the threshold is not an incident.
        if round(drop * 100) <= round(self.drop * 100):
            return None
        if round((confirm_base - confirm_now) * 100) > round(self.confirm_tolerance * 100):
            return None
        return DriftIncident(
            site=site,
            field=field,
            watch_tier=watch_tier,
            confirm_tier=confirm_tier,
            baseline_fill_rate=baseline,
            current_fill_rate=current,
            confirm_baseline=confirm_base,
            confirm_current=confirm_now,
        )
