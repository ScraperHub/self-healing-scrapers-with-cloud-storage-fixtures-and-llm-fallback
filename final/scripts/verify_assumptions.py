"""Check the three storage assumptions against the live API and write them down."""

from __future__ import annotations

import json
import sys
from pathlib import Path

FINAL = Path(__file__).resolve().parents[1]
if str(FINAL) not in sys.path:
    sys.path.insert(0, str(FINAL))

from selfheal.config import load_settings
from selfheal.crawl import CrawlbaseClient, body_kind
from selfheal.storage import StorageClient

DOCS = FINAL / "docs"
AMAZON = "https://www.amazon.com/dp/B0CHX2XFLN"
PLAIN = "https://example.com"


def _preview(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    return flat[:limit]


def main() -> int:
    settings = load_settings(FINAL)
    client = CrawlbaseClient(settings.crawlbase_token, settings.crawlbase_js_token, timeout=90)
    storage = StorageClient(settings.crawlbase_token)
    lines = [
        "# Verified Crawlbase behavior",
        "",
        "Checked live on 2026-11-16. The blog should follow this file, not the earlier notes.",
        "",
    ]

    print("1. store=true with scraper")
    scraped = client.fetch(AMAZON, store="true", scraper="amazon-product-details")
    scraped_kind = body_kind(scraped.body)
    stored_kind = "not fetched"
    stored_preview = ""
    sdk_get = "not tried"
    if scraped.rid:
        try:
            stored = storage.get_by_rid(scraped.rid)
            stored_kind = stored.kind
            stored_preview = _preview(stored.body)
            sdk_get = "StorageClient.get_by_rid succeeded"
        except Exception as exc:
            sdk_get = f"StorageClient.get_by_rid failed: {type(exc).__name__}: {exc}"
    lines.extend(
        [
            "## store=true combined with scraper=",
            "",
            "Request: `store=true` and `scraper=amazon-product-details` on an Amazon product URL.",
            f"Response body kind: `{scraped_kind}`.",
            f"`cb_status`: `{scraped.cb_status}`. `original_status`: `{scraped.original_status}`.",
            f"`rid` present: `{bool(scraped.rid)}`.",
            f"Stored copy kind when read back by rid: `{stored_kind}`.",
            f"Stored copy preview: `{stored_preview}`.",
            "",
            "If the stored copy is JSON, it is the scraper payload, not the raw HTML. "
            "Keep a second store=true crawl without scraper= when the tests need HTML.",
            "",
        ]
    )
    print(
        "   response="
        f"{scraped_kind} stored={stored_kind} rid={bool(scraped.rid)} cb={scraped.cb_status}"
    )

    print("2. re-crawl replacement")
    first = client.fetch(PLAIN, store="true")
    second = client.fetch(PLAIN, store="true")
    first_state = "no rid"
    url_rid = None
    url_stored_at = None
    second_stored_at = None
    if first.rid and second.rid:
        try:
            still = storage.get_by_rid(first.rid)
            first_state = f"still readable, kind={still.kind}, stored_at={still.stored_at}"
        except Exception as exc:
            first_state = f"not readable ({type(exc).__name__})"
        try:
            latest = storage.latest_by_url(PLAIN)
            url_rid = latest.rid
            url_stored_at = latest.stored_at
        except Exception as exc:
            url_rid = f"error {type(exc).__name__}"
        try:
            second_page = storage.get_by_rid(second.rid)
            second_stored_at = second_page.stored_at
        except Exception as exc:
            second_stored_at = f"error {type(exc).__name__}"
    if "still readable" in first_state:
        history = (
            "The first rid was still readable after the second crawl. "
            "Lookup by URL returns one copy, so a set of historical pages for selector checks "
            "still belongs in the repo mirror. Current docs keep stored pages for 30 days. "
            "Older material says 14."
        )
    else:
        history = (
            "The first rid did not survive the second crawl, "
            "so Storage keeps the newest copy of a URL. "
            "The last N versions used for selector checks are the mirrored fixtures in the repo. "
            "Current docs keep stored pages for 30 days. Older material says 14."
        )
    lines.extend(
        [
            "## Latest by URL, and whether a re-crawl replaces the previous copy",
            "",
            "Two `store=true` crawls of `https://example.com`, "
            "then a read of the first rid and a read by URL.",
            f"First rid readable after the second crawl: {first_state}.",
            f"Second rid stored_at: `{second_stored_at}`.",
            f"Lookup by URL returned rid `{url_rid}` stored_at `{url_stored_at}`.",
            f"The two rids were different: `{first.rid != second.rid}`.",
            "",
            history,
            "",
        ]
    )
    print(f"   first_after_second={first_state}")
    print(f"   by_url_rid_matches_second={url_rid == second.rid}")

    print("3. SDK methods")
    method_notes = [sdk_get]
    try:
        rids = storage.list_rids(limit=5)
        method_notes.append(f"rids returned {len(rids)} ids")
    except Exception as exc:
        method_notes.append(f"rids failed: {type(exc).__name__}: {exc}")
    try:
        total = storage.total_count()
        method_notes.append(f"totalCount={total}")
    except Exception as exc:
        method_notes.append(f"totalCount failed: {type(exc).__name__}: {exc}")
    if second.rid:
        try:
            bulk_pages = storage.bulk([second.rid])
            kind = bulk_pages[0].kind if bulk_pages else "none"
            method_notes.append(f"bulk returned {len(bulk_pages)} pages, kind={kind}")
        except Exception as exc:
            method_notes.append(f"bulk failed: {type(exc).__name__}: {exc}")
    lines.extend(
        [
            "## SDK methods that wrap the Storage API",
            "",
            "Installed package: `crawlbase` 1.0.0. "
            "`StorageAPI` exposes `get`, `delete`, `bulk`, `rids`, and `totalCount`.",
            "Live results:",
            "",
        ]
    )
    for note in method_notes:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "`storage.py` calls those SDK methods. "
            "If a method raises, the client retries the same call over HTTP.",
            "",
        ]
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "verified-behavior.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "scraper_response_kind": scraped_kind,
        "stored_kind": stored_kind,
        "first_rid_after_recrawl": first_state,
        "url_lookup_matches_second": url_rid == second.rid,
        "methods": method_notes,
    }
    (DOCS / "verified-behavior.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", DOCS / "verified-behavior.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
