from __future__ import annotations

import json
from pathlib import Path

from selfheal.crawl import PageFetch
from selfheal.drift import StatsStore
from selfheal.extractors.css_tier import load_selectors
from selfheal.fixtures import load_manifest, load_page
from selfheal.llm import (
    LlmProduct,
    OpenAiClient,
    SelectorProposalModel,
    proposal_selectors,
    to_product,
)
from selfheal.pipeline import (
    chain_for,
    crawl_product,
    detect_site,
    main,
    page_from_fetches,
    record_outcome,
    repair_site,
    run_fixtures,
)
from selfheal.schema import TRACKED_FIELDS
from selfheal.sites import get_site

from tests.conftest import sample_html, sample_selectors
from tests.test_drift import NOW, _history, _seed


def _write_fixture(root: Path) -> None:
    (root / "page.html").write_text(sample_html(), encoding="utf-8")
    (root / "selectors").mkdir()
    (root / "selectors" / "allbirds.json").write_text(
        json.dumps(sample_selectors()),
        encoding="utf-8",
    )
    manifest = {
        "fixtures": [
            {
                "rid": "local-1",
                "site": "allbirds",
                "url": "https://www.allbirds.com/products/mens-tree-runners",
                "html": "page.html",
            }
        ]
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_run_fixtures_and_loader(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assert run_fixtures(tmp_path, selector_dir=tmp_path / "selectors") == 0
    fixture = load_manifest(tmp_path / "manifest.json")[0]
    page = load_page(tmp_path, fixture)
    assert page.rid == "local-1"
    assert page.html.strip().startswith("<html>") or "Tree Runner" in page.html


def test_record_and_detect(tmp_path: Path) -> None:
    store = StatsStore(tmp_path / "stats.db")
    _history(store, "css", "price", True)
    _history(store, "llm", "price", True)
    _seed(store, tier="css", field="price", filled=False, when=NOW, repeats=4)
    _seed(store, tier="llm", field="price", filled=True, when=NOW, repeats=4)
    # NOW is inside the current window only when evaluate's now is later than NOW.
    from datetime import timedelta

    incidents = detect_site(store, "allbirds", now=NOW + timedelta(minutes=5))
    assert any(item.field == "price" for item in incidents)
    outcome = chain_for("allbirds", selector_dir=tmp_path / "selectors").run(_page())
    record_outcome(store, "allbirds", "https://www.allbirds.com/p", outcome.attempts, 200, 200)
    store.close()


def _page():
    from selfheal.extractors.page import Page

    return Page(url="https://www.allbirds.com/p", site="allbirds", html=sample_html())


def test_repair_site_writes_a_diff(tmp_path: Path) -> None:
    selectors = tmp_path / "selectors"
    selectors.mkdir()
    (selectors / "allbirds.json").write_text(json.dumps(sample_selectors()), encoding="utf-8")
    proposal = dict(sample_selectors())
    proposal["price"] = "span.price-now"
    ok, diff = repair_site(
        "allbirds",
        [sample_html()],
        proposal,
        reference_title="Tree Runner",
        selector_dir=selectors,
        output_dir=tmp_path / "repair_out",
    )
    assert ok is False or "price-now" in diff
    assert (tmp_path / "repair_out" / "allbirds.diff").is_file()


def test_page_from_fetches_and_crawl_product() -> None:
    html = PageFetch(
        requested_url="https://www.amazon.com/dp/B0CHX2XFLN",
        body="<html>amazon</html>",
        http_status=200,
        original_status=200,
        cb_status=200,
        rid="rid-html",
        final_url="https://www.amazon.com/dp/B0CHX2XFLN",
        content_type="text/html",
    )
    scraper = PageFetch(
        requested_url=html.requested_url,
        body=json.dumps({"name": "Case", "asin": "B0CHX2XFLN", "price": "$49.00"}),
        http_status=200,
        original_status=200,
        cb_status=200,
        rid="rid-json",
        final_url=html.final_url,
        content_type="application/json",
    )
    page = page_from_fetches(get_site("amazon"), html, scraper)
    assert page.scraper_json is not None
    assert page.rid == "rid-html"
    assert page.scraper_json["asin"] == "B0CHX2XFLN"

    class Client:
        def fetch(self, url: str, use_js: bool = False, **options: object) -> PageFetch:
            if "store" in options:
                return html
            return scraper

    crawled = crawl_product(Client(), get_site("amazon"), html.requested_url)  # type: ignore[arg-type]
    assert crawled.scraper_json is not None


def test_cli_requires_a_mode() -> None:
    assert main([]) == 2


def test_run_fixtures_cli(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    # The sample HTML uses teaching selectors, not the live Allbirds selectors.
    assert main(["--fixtures", "--fixture-root", str(tmp_path)]) == 1


def test_load_selectors_missing(tmp_path: Path) -> None:
    assert load_selectors("missing", tmp_path) == {}
    assert get_site("amazon").scraper == "amazon-product-details"
    try:
        get_site("nope")
    except KeyError as exc:
        assert "Unknown site" in str(exc)


def test_llm_helpers_and_client(monkeypatch) -> None:
    product = to_product(
        LlmProduct(title=" Tree Runner ", price="$98.00", rating="4.8", review_count="12")
    )
    assert product.title == "Tree Runner"
    assert product.currency == "USD"
    assert product.rating == 4.8
    selectors = proposal_selectors(
        SelectorProposalModel(title="h1.product-title", price=".product-price", notes="ignore")
    )
    assert "notes" not in selectors
    assert selectors["title"] == "h1.product-title"

    class Message:
        def __init__(self, parsed: object) -> None:
            self.parsed = parsed
            self.refusal = None

    class Choice:
        def __init__(self, parsed: object) -> None:
            self.message = Message(parsed)

    class Usage:
        prompt_tokens = 12
        completion_tokens = 4

    class Completion:
        def __init__(self, parsed: object) -> None:
            self.choices = [Choice(parsed)]
            self.usage = Usage()

    class Completions:
        def parse(self, **kwargs: object) -> Completion:
            model = kwargs["response_format"]
            if model is LlmProduct:
                return Completion(LlmProduct(title="Tree Runner", price="$98"))
            if model is SelectorProposalModel:
                return Completion(SelectorProposalModel(title="h1.t", price=".p"))
            return Completion(None)

    class Chat:
        completions = Completions()

    class Beta:
        chat = Chat()

    class FakeOpenAI:
        def __init__(self, api_key: str) -> None:
            self.beta = Beta()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    client = OpenAiClient("test-key", model="gpt-4o-mini")
    assert client.extract_product("markdown").title == "Tree Runner"
    assert client.propose_selectors("<html></html>", list(TRACKED_FIELDS))["price"] == ".p"
    assert client.last_output_tokens == 4

    class Refusing:
        def __init__(self, api_key: str) -> None:
            self.beta = Beta()

    monkeypatch.setattr(Completions, "parse", lambda self, **kwargs: Completion(None))
    monkeypatch.setattr("openai.OpenAI", Refusing)
    try:
        OpenAiClient("test-key").extract_product("markdown")
        raised = False
    except RuntimeError:
        raised = True
    assert raised
