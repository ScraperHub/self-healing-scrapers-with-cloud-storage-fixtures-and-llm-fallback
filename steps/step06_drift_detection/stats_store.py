"""SQLite samples for per-field fill rate. Fetch failures stay out of the average."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Sample:
    recorded_at: datetime
    site: str
    tier: str
    field: str
    filled: bool
    original_status: int
    cb_status: int


class StatsStore:
    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE samples (
                recorded_at TEXT NOT NULL,
                site TEXT NOT NULL,
                tier TEXT NOT NULL,
                field TEXT NOT NULL,
                filled INTEGER NOT NULL,
                original_status INTEGER,
                cb_status INTEGER
            )
            """
        )

    def record(self, sample: Sample) -> None:
        self._conn.execute(
            """
            INSERT INTO samples (
                recorded_at, site, tier, field, filled, original_status, cb_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample.recorded_at.astimezone(UTC).isoformat(),
                sample.site,
                sample.tier,
                sample.field,
                1 if sample.filled else 0,
                sample.original_status,
                sample.cb_status,
            ),
        )
        self._conn.commit()

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
