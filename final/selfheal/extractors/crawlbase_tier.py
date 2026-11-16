"""Tier 1: Crawlbase built-in scraper or autoparse JSON."""

from __future__ import annotations

from selfheal.extractors.mapping import product_from_mapping
from selfheal.extractors.page import Page
from selfheal.schema import Result, failed_result, success_result


class CrawlbaseTier:
    tier = "crawlbase"

    def extract(self, page: Page) -> Result:
        if not page.scraper_json:
            return failed_result(self.tier, "no scraper payload")
        product = product_from_mapping(page.scraper_json)
        if product is None:
            return failed_result(self.tier, "scraper payload has no title")
        return success_result(self.tier, product)
