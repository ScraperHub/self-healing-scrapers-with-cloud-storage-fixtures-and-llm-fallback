from __future__ import annotations

from pathlib import Path

from selfheal.repair import (
    break_selector_targets,
    clean_html,
    selectors_diff,
    shifted_selectors,
    slim_html,
    validate_selectors,
    write_diff,
)
from selfheal.schema import ProductSchema
from tests.conftest import sample_html, sample_selectors


def test_validator_accepts_selectors_that_hit_every_snapshot() -> None:
    html = sample_html()
    report = validate_selectors(sample_selectors(), [html, html])
    assert report.ok
    assert report.extracted[0]["title"] == "Tree Runner"


def test_validator_rejects_a_snapshot_that_misses_price() -> None:
    broken = sample_html().replace('class="product-price"', 'class="gone"')
    report = validate_selectors(sample_selectors(), [sample_html(), broken])
    assert not report.ok
    assert any("price" in item for item in report.failures)


def test_validator_checks_the_llm_value_on_the_last_snapshot() -> None:
    report = validate_selectors(
        sample_selectors(),
        [sample_html()],
        reference=ProductSchema(title="Completely different shoe"),
    )
    assert not report.ok
    assert any("disagrees" in item for item in report.failures)

    agreed = validate_selectors(
        sample_selectors(),
        [sample_html()],
        reference=ProductSchema(title="Tree Runner"),
    )
    assert agreed.ok


def test_validator_needs_snapshots() -> None:
    report = validate_selectors(sample_selectors(), [])
    assert not report.ok


def test_diff_and_write(tmp_path: Path) -> None:
    updated = dict(sample_selectors())
    updated["title"] = "h1.product-title-shifted"
    diff = selectors_diff(sample_selectors(), updated, "selectors/allbirds.json")
    assert "product-title-shifted" in diff
    path = write_diff(diff, tmp_path / "repair_out" / "allbirds.diff")
    assert path.read_text(encoding="utf-8") == diff


def test_clean_html_drops_scripts_and_shift_renames_classes() -> None:
    cleaned = clean_html(sample_html())
    assert "secret" not in cleaned
    assert "Tree Runner" in cleaned
    assert "script" not in slim_html(sample_html())
    mutated = break_selector_targets(sample_html(), sample_selectors())
    assert "product-title-shifted" in mutated
    assert 'product-title"' not in mutated.replace("product-title-shifted", "")
    shifted = shifted_selectors(sample_selectors())
    assert shifted["title"] == "h1.product-title-shifted"
    report = validate_selectors(shifted, [mutated], required=("title", "price"))
    assert report.ok
