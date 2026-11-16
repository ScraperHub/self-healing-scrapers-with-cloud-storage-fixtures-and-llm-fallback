"""Mirror stored pages into fixtures/ so replay tests survive the retention window."""

from __future__ import annotations

import json
import sys
from pathlib import Path

FINAL = Path(__file__).resolve().parents[1]
if str(FINAL) not in sys.path:
    sys.path.insert(0, str(FINAL))

from selfheal.config import load_settings
from selfheal.crawl import CrawlbaseClient, CrawlError, body_kind, loads_json_object
from selfheal.extractors.css_tier import CssTier
from selfheal.extractors.mapping import product_from_mapping
from selfheal.extractors.page import Page
from selfheal.fixtures import Fixture, load_manifest
from selfheal.pipeline import dump_manifest
from selfheal.repair import slim_html
from selfheal.schema import fill_rate
from selfheal.sites import SITES

FIXTURES = FINAL / "fixtures"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    settings = load_settings(FINAL)
    client = CrawlbaseClient(settings.crawlbase_token, settings.crawlbase_js_token, timeout=90)
    fixtures: list[Fixture] = []
    manifest_path = FIXTURES / "manifest.json"
    done: set[str] = set()
    if manifest_path.is_file():
        fixtures = load_manifest(manifest_path)
        done = {item.url for item in fixtures}
    failures: list[str] = []

    for site in SITES.values():
        for index, url in enumerate(site.urls, start=1):
            if url in done:
                print(f"skip {site.name} {index}", flush=True)
                continue
            print(f"crawl {site.name} {index} {url}", flush=True)
            try:
                html_fetch = client.fetch(url, store="true")
            except CrawlError as exc:
                failures.append(f"{site.name} html {url} {exc}")
                continue
            if (
                html_fetch.cb_status != 200
                or html_fetch.original_status != 200
                or not html_fetch.rid
                or body_kind(html_fetch.body) != "html"
            ):
                failures.append(
                    f"{site.name} html {url} cb={html_fetch.cb_status} "
                    f"original={html_fetch.original_status} kind={body_kind(html_fetch.body)}"
                )
                continue
            rid = html_fetch.rid
            folder = FIXTURES / site.name
            html_rel = f"{site.name}/{rid}.html"
            html_text = slim_html(html_fetch.body)
            _write(folder / f"{rid}.html", html_text)
            scraper_rel = None
            generic_rel = None
            markdown_rel = None

            if site.scraper:
                try:
                    scraped = client.fetch(url, scraper=site.scraper)
                except CrawlError as exc:
                    failures.append(f"{site.name} scraper {url} {exc}")
                    (folder / f"{rid}.html").unlink(missing_ok=True)
                    continue
                payload = loads_json_object(scraped.body) if scraped else None
                product = product_from_mapping(payload) if payload else None
                rate = fill_rate(product) if product else 0.0
                if (
                    product is None
                    or scraped is None
                    or scraped.cb_status != 200
                    or rate < site.min_fill_rate
                ):
                    status = scraped.cb_status if scraped is not None else "error"
                    failures.append(f"{site.name} scraper {url} cb={status} fill={rate:.2f}")
                    (folder / f"{rid}.html").unlink(missing_ok=True)
                    continue
                scraper_rel = f"{site.name}/{rid}.json"
                _write(folder / f"{rid}.json", json.dumps(payload, indent=2) + "\n")
                print(f"  scraper title={product.title[:50]} fill={rate:.2f}")
            else:
                try:
                    generic = client.fetch(url, scraper="generic-extractor")
                except CrawlError as exc:
                    failures.append(f"{site.name} generic {url} {exc}")
                    generic = None
                payload = loads_json_object(generic.body) if generic else None
                if generic is not None and generic.cb_status == 200 and payload:
                    generic_rel = f"{site.name}/{rid}.json"
                    _write(folder / f"{rid}.json", json.dumps(payload, indent=2) + "\n")
                try:
                    markdown = client.fetch(url, format="md", md_readability="true")
                except CrawlError as exc:
                    failures.append(f"{site.name} markdown {url} {exc}")
                    markdown = None
                if markdown and markdown.cb_status == 200 and len(markdown.body) > 100:
                    markdown_rel = f"{site.name}/{rid}.md"
                    _write(folder / f"{rid}.md", markdown.body)
                css = CssTier().extract(Page(url=url, site=site.name, html=html_text))
                if css.fill_rate < site.min_fill_rate:
                    failures.append(f"{site.name} css {url} fill={css.fill_rate:.2f}")
                    for suffix in (".html", ".json", ".md"):
                        (folder / f"{rid}{suffix}").unlink(missing_ok=True)
                    continue

            fixtures.append(
                Fixture(
                    rid=rid,
                    site=site.name,
                    url=html_fetch.final_url or url,
                    html=html_rel,
                    scraper_json=scraper_rel,
                    generic_json=generic_rel,
                    markdown=markdown_rel,
                    original_status=html_fetch.original_status,
                    cb_status=html_fetch.cb_status,
                )
            )
            print(f"  stored rid={rid}")

    dump_manifest(FIXTURES / "manifest.json", fixtures)
    print(f"wrote {len(fixtures)} fixtures")
    if failures:
        print("FAILURES")
        for item in failures:
            print(" -", item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
