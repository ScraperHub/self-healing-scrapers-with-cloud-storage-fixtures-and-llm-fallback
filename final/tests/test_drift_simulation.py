"""Mutate a stored page and prove the chain, the detector, and the repair step."""

from __future__ import annotations

from datetime import timedelta

from selfheal.drift import DriftDetector, StatsStore
from selfheal.extractors.chain import TierChain
from selfheal.extractors.css_tier import CssTier
from selfheal.extractors.llm_tier import LlmTier
from selfheal.extractors.page import Page
from selfheal.fixtures import Fixture, load_page
from selfheal.repair import (
    break_selector_targets,
    selectors_diff,
    shifted_selectors,
    validate_selectors,
    write_diff,
)
from tests.conftest import full_product, sample_html, sample_selectors
from tests.test_drift import NOW, _history, _seed
from tests.test_tiers import FakeModel


def test_simulated_drift_repairs_against_snapshots(tmp_path) -> None:
    html_path = tmp_path / "fixtures" / "allbirds" / "local.html"
    html_path.parent.mkdir(parents=True)
    html_path.write_text(sample_html(), encoding="utf-8")
    fixture = Fixture(
        rid="local",
        site="allbirds",
        url="https://www.allbirds.com/products/mens-tree-runners",
        html="allbirds/local.html",
    )
    page = load_page(tmp_path / "fixtures", fixture)
    selectors = sample_selectors()
    css = CssTier(selectors=selectors)
    healthy = css.extract(page)
    assert healthy.product is not None
    assert healthy.fill_rate >= 0.75

    mutated = break_selector_targets(page.html, selectors)
    broken_page = Page(
        url=page.url,
        site="allbirds",
        html=mutated,
        markdown="# Tree Runner\n\n$98.00",
        original_status=200,
        cb_status=200,
    )
    assert css.extract(broken_page).product is None

    chain = TierChain([css, LlmTier(FakeModel())], min_fill_rate=0.75)
    outcome = chain.run(broken_page)
    assert outcome.winner is not None
    assert outcome.winner.tier == "llm"
    assert outcome.attempts[0].tier == "css"
    assert outcome.attempts[0].product is None

    store = StatsStore(tmp_path / "drift.db")
    _history(store, "css", "title", True)
    _history(store, "llm", "title", True)
    _seed(store, tier="css", field="title", filled=False, when=NOW - timedelta(hours=2), repeats=4)
    _seed(store, tier="llm", field="title", filled=True, when=NOW - timedelta(hours=2), repeats=4)
    incidents = DriftDetector(store).evaluate("allbirds", ["title"], "css", "llm", now=NOW)
    assert incidents
    assert incidents[0].watch_tier == "css"
    store.close()

    proposal = shifted_selectors(selectors)
    snapshots = [mutated, mutated.replace("Tree Runner", "Tree Runner")]
    report = validate_selectors(
        proposal,
        snapshots,
        required=("title", "price"),
        reference=full_product(),
    )
    assert report.ok
    diff = selectors_diff(selectors, proposal, "selectors/allbirds.json")
    written = write_diff(diff, tmp_path / "repair_out" / "allbirds.diff")
    assert "product-title-shifted" in written.read_text(encoding="utf-8")
