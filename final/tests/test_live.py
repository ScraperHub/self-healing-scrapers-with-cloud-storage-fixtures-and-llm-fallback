"""Live checks. These spend Crawlbase credits and a few OpenAI tokens."""

from __future__ import annotations

import json

import pytest
from selfheal.config import load_settings
from selfheal.crawl import CrawlbaseClient, body_kind
from selfheal.llm import OpenAiClient
from selfheal.repair import validate_selectors
from selfheal.schema import TRACKED_FIELDS
from selfheal.sites import get_site
from selfheal.storage import StorageClient

from tests.conftest import sample_html

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def crawler(settings):
    return CrawlbaseClient(settings.crawlbase_token, settings.crawlbase_js_token, timeout=90)


def test_store_true_returns_an_rid_and_storage_reads_it_back(crawler, settings) -> None:
    page = crawler.fetch("https://example.com", store="true")
    assert page.cb_status == 200, page.cb_status
    assert page.rid
    stored = StorageClient(settings.crawlbase_token).get_by_rid(page.rid)
    assert stored.body
    assert stored.rid in {page.rid, None} or stored.body
    assert "Example Domain" in stored.body or body_kind(stored.body) in {"html", "text"}


def test_named_scraper_and_autoparse(crawler) -> None:
    urls = get_site("amazon").urls[1:] + get_site("amazon").urls[:1]
    assert _first_product_name(crawler, urls, scraper="amazon-product-details")
    assert _first_product_name(crawler, urls, autoparse="true")


def _first_product_name(crawler: CrawlbaseClient, urls: tuple[str, ...], **options: str) -> str:
    last_cb = 0
    last_original: int | None = None
    for url in urls:
        page = crawler.fetch(url, **options)
        last_cb = page.cb_status or 0
        last_original = page.original_status
        if page.cb_status != 200:
            continue
        try:
            loaded = json.loads(page.body)
        except json.JSONDecodeError:
            continue
        if not isinstance(loaded, dict):
            continue
        name = loaded.get("name") or loaded.get("title") or loaded.get("main_content")
        if isinstance(name, str) and name.strip():
            return name.strip()
    raise AssertionError(f"no product name cb={last_cb} original={last_original}")


def test_generic_extractor_and_markdown(crawler) -> None:
    generic_ok = False
    markdown_ok = False
    last_cb = 0
    last_original: int | None = None
    for url in get_site("allbirds").urls:
        if not generic_ok:
            generic = crawler.fetch(url, scraper="generic-extractor")
            if generic.cb_status == 200:
                payload = json.loads(generic.body)
                if isinstance(payload, dict) and (payload.get("title") or payload.get("headings")):
                    generic_ok = True
        markdown = crawler.fetch(url, format="md", md_readability="true")
        last_cb = markdown.cb_status or 0
        last_original = markdown.original_status
        if markdown.cb_status == 200 and len(markdown.body) > 40:
            if "US" in markdown.body or "Tree" in markdown.body:
                markdown_ok = True
        if generic_ok and markdown_ok:
            break
    assert generic_ok
    assert markdown_ok, (last_cb, last_original)


def test_real_llm_extraction_and_selector_proposal(settings) -> None:
    client = OpenAiClient(settings.openai_api_key, settings.openai_model)
    product = client.extract_product(
        "# Men's Tree Runners\n\nBrand: Allbirds\n\nPrice: $100.00\n\nIn stock\n\nSKU: TR-M\n"
    )
    assert "Tree" in product.title
    assert product.price
    assert client.last_input_tokens > 0

    proposal = client.propose_selectors(sample_html(), list(TRACKED_FIELDS))
    assert "title" in proposal
    assert "price" in proposal
    report = validate_selectors(
        proposal, [sample_html(), sample_html()], required=("title", "price")
    )
    assert report.ok, report.failures
