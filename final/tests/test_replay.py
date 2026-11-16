"""Replay mirrored pages. No network."""

from __future__ import annotations

from pathlib import Path

import pytest
from selfheal.extractors.chain import TierChain
from selfheal.extractors.crawlbase_tier import CrawlbaseTier
from selfheal.extractors.css_tier import CssTier
from selfheal.extractors.generic_tier import GenericTier
from selfheal.fixtures import Fixture, load_manifest, load_page
from selfheal.pipeline import FIXTURE_ROOT, SELECTOR_DIR
from selfheal.sites import get_site

pytestmark = pytest.mark.replay


def _cases() -> list[Fixture]:
    path = FIXTURE_ROOT / "manifest.json"
    if not path.is_file():
        return []
    return load_manifest(path)


_FIXTURES = _cases()


@pytest.mark.parametrize(
    "fixture",
    _FIXTURES or [None],
    ids=[item.rid for item in _FIXTURES] or ["missing-manifest"],
)
def test_replay_fixture(fixture: Fixture | None) -> None:
    assert fixture is not None, "fixtures/manifest.json is missing"
    page = load_page(FIXTURE_ROOT, fixture)
    chain = TierChain(
        [CrawlbaseTier(), CssTier(directory=SELECTOR_DIR), GenericTier()],
        min_fill_rate=get_site(fixture.site).min_fill_rate,
    )
    outcome = chain.run(page)
    assert outcome.winner is not None, fixture.rid
    assert outcome.winner.product is not None
    assert outcome.winner.fill_rate >= get_site(fixture.site).min_fill_rate
    assert page.original_status == 200
    assert Path(FIXTURE_ROOT / fixture.html).is_file()
