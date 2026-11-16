"""One method. Tiers stay pure so tests can call them without the network."""

from __future__ import annotations

from typing import Protocol

from schema import ProductSchema


class Extractor(Protocol):
    tier: str

    def extract(self, page: str) -> ProductSchema:
        """Return a product parsed from this page."""
