from __future__ import annotations

from selfheal.extractors.chain import TierChain
from selfheal.extractors.crawlbase_tier import CrawlbaseTier
from selfheal.extractors.css_tier import CssTier
from selfheal.extractors.generic_tier import GenericTier
from selfheal.extractors.llm_tier import LlmTier
from selfheal.extractors.page import Page
from selfheal.schema import ProductSchema, failed_result
from tests.conftest import full_product, sample_html, sample_page, sample_selectors


def test_crawlbase_tier_maps_amazon_and_walmart() -> None:
    amazon = Page(
        url="https://www.amazon.com/dp/B0CHX2XFLN",
        site="amazon",
        scraper_json={
            "name": "Apple iPhone Silicone Case",
            "asin": "B0CHX2XFLN",
            "brand": "Apple",
            "price": "$49.00",
            "availability": "In Stock",
            "rating": 4.7,
            "reviews_count": 12483,
        },
    )
    product = CrawlbaseTier().extract(amazon).product
    assert product is not None
    assert product.title.startswith("Apple")
    assert product.sku == "B0CHX2XFLN"
    assert product.currency == "USD"
    assert product.review_count == 12483

    walmart = Page(
        url="https://www.walmart.com/ip/1",
        site="walmart",
        scraper_json={
            "title": "Meta Quest 3",
            "product_id": "3551794083",
            "price": "$649.99",
            "inStock": True,
            "rating": "4.7",
        },
    )
    parsed = CrawlbaseTier().extract(walmart).product
    assert parsed is not None
    assert parsed.sku == "3551794083"
    assert parsed.availability == "In Stock"


def test_crawlbase_tier_rejects_empty_payload() -> None:
    assert CrawlbaseTier().extract(Page(url="https://example.com")).error == "no scraper payload"
    missing = CrawlbaseTier().extract(
        Page(url="https://example.com", scraper_json={"brand": "Acme"})
    )
    assert missing.product is None


def test_css_tier_reads_selectors() -> None:
    result = CssTier(selectors=sample_selectors()).extract(sample_page())
    assert result.product is not None
    assert result.product.title == "Tree Runner"
    assert result.fill_rate == 1.0


def test_css_tier_misses_title_when_classes_change() -> None:
    html = sample_html().replace("product-title", "product-title-shifted")
    result = CssTier(selectors=sample_selectors()).extract(sample_page(html=html))
    assert result.product is None


def test_css_tier_requires_html_and_selectors() -> None:
    assert (
        CssTier(selectors=sample_selectors()).extract(Page(url="https://example.com")).error
        == "html is empty"
    )
    assert "no selectors" in (CssTier(selectors={}).extract(sample_page()).error or "")


def test_generic_tier_pulls_title_and_price() -> None:
    page = Page(
        url="https://www.allbirds.com/products/mens-tree-runners",
        site="allbirds",
        generic_json={
            "title": "Men's Tree Runners",
            "headings": {"h1": ["Men's Tree Runners"]},
            "main_content": "A light shoe. Price $98.00. In stock.",
        },
    )
    result = GenericTier().extract(page)
    assert result.product is not None
    assert result.product.price == "$98.00"
    assert result.fill_rate < 0.75


def test_generic_tier_uses_heading_and_rejects_gaps() -> None:
    page = Page(
        url="https://www.allbirds.com/p",
        generic_json={"headings": {"h1": ["Only a heading"]}},
    )
    assert GenericTier().extract(page).product is not None
    assert GenericTier().extract(Page(url="https://www.allbirds.com/p")).product is None


class FakeModel:
    def __init__(self, product: ProductSchema | None = None, error: str | None = None) -> None:
        self.product = product or full_product()
        self.error = error

    def extract_product(self, markdown: str) -> ProductSchema:
        if self.error:
            raise RuntimeError(self.error)
        return self.product


def test_llm_tier_accepts_a_parsed_product() -> None:
    page = sample_page(markdown="# Tree Runner\n\n$98.00")
    result = LlmTier(FakeModel()).extract(page)
    assert result.tier == "llm"
    assert result.product is not None
    assert result.fill_rate == 1.0


def test_llm_tier_reports_empty_input_and_model_errors() -> None:
    assert LlmTier(FakeModel()).extract(sample_page(markdown="")).product is None
    crashed = LlmTier(FakeModel(error="timeout")).extract(sample_page(markdown="hello"))
    assert "timeout" in (crashed.error or "")
    empty = ProductSchema(title="  ")
    assert LlmTier(FakeModel(product=empty)).extract(sample_page(markdown="hello")).product is None


class First:
    tier = "crawlbase"

    def extract(self, page: Page):
        return failed_result(self.tier, "miss")


class Second:
    tier = "css"
    called = False

    def extract(self, page: Page):
        self.called = True
        raise RuntimeError("selector boom")


class Third:
    tier = "llm"

    def extract(self, page: Page):
        from selfheal.schema import success_result

        return success_result(self.tier, full_product())


def test_chain_stops_at_the_first_tier_that_clears_the_bar() -> None:
    winner = Third()
    css = Second()
    outcome = TierChain([First(), css, winner]).run(sample_page())
    assert outcome.winner is not None
    assert outcome.winner.tier == "llm"
    assert css.called is True
    assert [item.tier for item in outcome.attempts] == ["crawlbase", "css", "llm"]


def test_chain_run_stops_before_later_tiers() -> None:
    class Early:
        tier = "crawlbase"

        def extract(self, page: Page):
            from selfheal.schema import success_result

            return success_result(self.tier, full_product())

    class Later:
        tier = "css"

        def extract(self, page: Page):
            raise AssertionError("should not run")

    outcome = TierChain([Early(), Later()]).run(sample_page())
    assert outcome.winner is not None
    assert len(outcome.attempts) == 1


def test_chain_observe_keeps_going_after_a_win() -> None:
    class Early:
        tier = "css"

        def extract(self, page: Page):
            from selfheal.schema import success_result

            return success_result(self.tier, full_product())

    class Later:
        tier = "llm"
        called = False

        def extract(self, page: Page):
            self.called = True
            return failed_result(self.tier, "not needed")

    later = Later()
    outcome = TierChain([Early(), later]).observe(sample_page())
    assert outcome.winner is not None
    assert later.called is True


def test_chain_returns_no_winner_under_the_bar() -> None:
    page = Page(
        url="https://www.allbirds.com/p",
        generic_json={"title": "Only title"},
    )
    outcome = TierChain([GenericTier()], min_fill_rate=0.75).run(page)
    assert outcome.winner is None
    assert outcome.attempts[0].product is not None
