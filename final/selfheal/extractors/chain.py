"""First tier that clears the fill-rate bar wins. Later tiers are the fallback."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from selfheal.extractors.base import Extractor
from selfheal.extractors.page import Page
from selfheal.schema import Result, failed_result


@dataclass
class ChainOutcome:
    winner: Result | None
    attempts: list[Result]


class TierChain:
    def __init__(self, extractors: Sequence[Extractor], min_fill_rate: float = 0.75) -> None:
        self.extractors = extractors
        self.min_fill_rate = min_fill_rate

    def run(self, page: Page) -> ChainOutcome:
        return self._execute(page, stop_early=True)

    def observe(self, page: Page) -> ChainOutcome:
        """Run every tier so drift stats see the ones that are rotting."""

        return self._execute(page, stop_early=False)

    def _execute(self, page: Page, stop_early: bool) -> ChainOutcome:
        attempts: list[Result] = []
        winner: Result | None = None
        for extractor in self.extractors:
            result = self._safe(extractor, page)
            attempts.append(result)
            if winner is None and self.accepts(result):
                winner = result
                if stop_early:
                    break
        return ChainOutcome(winner=winner, attempts=attempts)

    def accepts(self, result: Result) -> bool:
        if result.product is None:
            return False
        return result.fill_rate >= self.min_fill_rate

    def _safe(self, extractor: Extractor, page: Page) -> Result:
        try:
            return extractor.extract(page)
        except Exception as exc:
            return failed_result(extractor.tier, f"extractor crashed: {exc}")
