"""Wire crawl, extract, measure, and repair. Also the CLI."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from selfheal.crawl import CrawlbaseClient, PageFetch, loads_json_object
from selfheal.drift import DriftDetector, DriftIncident, StatsStore
from selfheal.extractors.chain import TierChain
from selfheal.extractors.crawlbase_tier import CrawlbaseTier
from selfheal.extractors.css_tier import CssTier, load_selectors
from selfheal.extractors.generic_tier import GenericTier
from selfheal.extractors.llm_tier import LlmTier
from selfheal.extractors.page import Page
from selfheal.fixtures import Fixture, load_manifest, load_page
from selfheal.repair import selectors_diff, validate_selectors, write_diff
from selfheal.schema import TRACKED_FIELDS, ProductSchema, Result
from selfheal.sites import Site, get_site

PACKAGE_ROOT = Path(__file__).resolve().parent
FINAL_ROOT = PACKAGE_ROOT.parent
FIXTURE_ROOT = FINAL_ROOT / "fixtures"
SELECTOR_DIR = PACKAGE_ROOT / "selectors"


def chain_for(
    site: str,
    llm: LlmTier | None = None,
    min_fill_rate: float | None = None,
    selector_dir: Path | None = None,
) -> TierChain:
    configured = get_site(site)
    rate = configured.min_fill_rate if min_fill_rate is None else min_fill_rate
    extractors: list[CrawlbaseTier | CssTier | GenericTier | LlmTier] = [
        CrawlbaseTier(),
        CssTier(directory=selector_dir or SELECTOR_DIR),
        GenericTier(),
    ]
    if llm is not None:
        extractors.append(llm)
    return TierChain(extractors, min_fill_rate=rate)


def page_from_fetches(
    site: Site,
    html_fetch: PageFetch | None = None,
    scraper_fetch: PageFetch | None = None,
    generic_fetch: PageFetch | None = None,
    markdown_fetch: PageFetch | None = None,
) -> Page:
    primary = html_fetch or scraper_fetch or generic_fetch or markdown_fetch
    if primary is None:
        raise ValueError("at least one fetch is required")
    return Page(
        url=primary.final_url or primary.requested_url,
        site=site.name,
        html=html_fetch.body if html_fetch else "",
        markdown=markdown_fetch.body if markdown_fetch else "",
        scraper_json=loads_json_object(scraper_fetch.body) if scraper_fetch else None,
        generic_json=loads_json_object(generic_fetch.body) if generic_fetch else None,
        original_status=primary.original_status,
        cb_status=primary.cb_status,
        rid=primary.rid,
    )


def record_outcome(
    store: StatsStore,
    site: str,
    url: str,
    outcome_attempts: list[Result],
    original_status: int | None,
    cb_status: int | None,
    recorded_at: datetime | None = None,
) -> None:
    moment = recorded_at or datetime.now(UTC)
    for result in outcome_attempts:
        store.record_fields(
            recorded_at=moment,
            site=site,
            url=url,
            tier=result.tier,
            field_nulls=result.field_nulls,
            original_status=original_status,
            cb_status=cb_status,
        )


def run_fixtures(
    fixture_root: Path | None = None,
    min_fill_rate: float | None = None,
    selector_dir: Path | None = None,
) -> int:
    root = fixture_root or FIXTURE_ROOT
    manifest = load_manifest(root / "manifest.json")
    failures = 0
    for fixture in manifest:
        page = load_page(root, fixture)
        outcome = chain_for(
            fixture.site,
            min_fill_rate=min_fill_rate,
            selector_dir=selector_dir,
        ).run(page)
        if outcome.winner is None or outcome.winner.product is None:
            failures += 1
            print(f"FAIL {fixture.site} {fixture.rid}")
            continue
        product = outcome.winner.product
        print(
            f"OK {fixture.site} tier={outcome.winner.tier} "
            f"fill={outcome.winner.fill_rate:.2f} title={product.title[:60]}"
        )
    return failures


def repair_site(
    site_name: str,
    html_snapshots: list[str],
    proposal: dict[str, str],
    reference_title: str | None = None,
    selector_dir: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[bool, str]:
    directory = selector_dir or SELECTOR_DIR
    current = load_selectors(site_name, directory)
    reference = ProductSchema(title=reference_title) if reference_title else None
    report = validate_selectors(proposal, html_snapshots, reference=reference)
    diff = selectors_diff(current, proposal, f"selectors/{site_name}.json")
    destination = (output_dir or (FINAL_ROOT / "repair_out")) / f"{site_name}.diff"
    write_diff(diff, destination)
    print(report.summary())
    print(diff)
    return report.ok, diff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the self-healing scraper pipeline")
    parser.add_argument("--fixtures", action="store_true", help="Replay mirrored fixtures")
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--min-fill-rate", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fixtures:
        return run_fixtures(args.fixture_root, args.min_fill_rate)
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


def crawl_product(client: CrawlbaseClient, site: Site, url: str) -> Page:
    """One stored HTML fetch, plus a scraper or generic-extractor call when it helps."""

    html_fetch = client.fetch(url, store="true")
    scraper_fetch = None
    generic_fetch = None
    if site.scraper:
        scraper_fetch = client.fetch(url, scraper=site.scraper)
    else:
        generic_fetch = client.fetch(url, scraper="generic-extractor")
    return page_from_fetches(site, html_fetch, scraper_fetch, generic_fetch)


def detect_site(
    store: StatsStore, site_name: str, now: datetime | None = None
) -> list[DriftIncident]:
    site = get_site(site_name)
    detector = DriftDetector(store)
    return detector.evaluate(
        site.name,
        list(TRACKED_FIELDS),
        site.watch_tier,
        site.confirm_tier,
        now=now,
    )


def dump_manifest(path: Path, fixtures: list[Fixture]) -> None:
    payload = {"fixtures": [fixture.__dict__ for fixture in fixtures]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
