"""Stop at the first tier that validates and clears the fill-rate bar."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from fill_rate import ProductSchema, fill_rate


class Extractor(Protocol):
    tier: str

    def extract(self, page: str) -> ProductSchema | None:
        """Return a product, or None when this tier cannot read the page."""


@dataclass
class Attempt:
    tier: str
    product: ProductSchema | None
    fill_rate: float
    error: str | None = None


@dataclass
class ChainOutcome:
    winner: Attempt | None
    attempts: list[Attempt]


class TierChain:
    def __init__(self, extractors: Sequence[Extractor], min_fill_rate: float = 0.75) -> None:
        self.extractors = extractors
        self.min_fill_rate = min_fill_rate

    def run(self, page: str) -> ChainOutcome:
        attempts: list[Attempt] = []
        winner: Attempt | None = None
        for extractor in self.extractors:
            attempt = self._safe(extractor, page)
            attempts.append(attempt)
            if winner is None and self._accepts(attempt):
                winner = attempt
                break
        return ChainOutcome(winner=winner, attempts=attempts)

    def _accepts(self, attempt: Attempt) -> bool:
        return attempt.product is not None and attempt.fill_rate >= self.min_fill_rate

    def _safe(self, extractor: Extractor, page: str) -> Attempt:
        try:
            product = extractor.extract(page)
        except Exception as exc:
            return Attempt(extractor.tier, None, 0.0, f"extractor crashed: {exc}")
        if product is None:
            return Attempt(extractor.tier, None, 0.0, "no product")
        return Attempt(extractor.tier, product, fill_rate(product))
