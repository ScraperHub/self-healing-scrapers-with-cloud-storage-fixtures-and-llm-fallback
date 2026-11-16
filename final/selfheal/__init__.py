"""Self-healing scraper framework: tiered extraction, drift detection, and repair."""

from selfheal.schema import TRACKED_FIELDS, ProductSchema, fill_rate

__all__ = ["TRACKED_FIELDS", "ProductSchema", "fill_rate"]
__version__ = "0.1.0"
