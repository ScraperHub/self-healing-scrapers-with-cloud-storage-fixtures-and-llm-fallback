"""Extractor protocol."""

from __future__ import annotations

from typing import Protocol

from selfheal.extractors.page import Page
from selfheal.schema import Result


class Extractor(Protocol):
    tier: str

    def extract(self, page: Page) -> Result:
        """Return a product or a failed result. Do not raise for bad pages."""
