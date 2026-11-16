# Verified Crawlbase behavior

Checked live on 2026-11-16. The blog should follow this file, not the earlier notes.

## store=true combined with scraper=

Request: `store=true` and `scraper=amazon-product-details` on an Amazon product URL.
Response body kind: `json`.
`cb_status`: `200`. `original_status`: `200`.
`rid` present: `True`.
Stored copy kind when read back by rid: `json`.
Stored copy preview: `{"name":"Apple iPhone 15 Pro Silicone Case with MagSafe - Winter Blue","price":null,"originalPrice":"","rawPrice":null,"currency":null,"canonicalUrl":"https://w`.

If the stored copy is JSON, it is the scraper payload, not the raw HTML. Keep a second store=true crawl without scraper= when the tests need HTML.

## Latest by URL, and whether a re-crawl replaces the previous copy

Two `store=true` crawls of `https://example.com`, then a read of the first rid and a read by URL.
First rid readable after the second crawl: still readable, kind=html, stored_at=2026-11-16T13:58:53+00:00.
Second rid stored_at: `2026-11-16T13:58:55+00:00`.
Lookup by URL returned rid `21b5ecad3842fdd252ffd12f` stored_at `2026-11-16T13:58:55+00:00`.
The two rids were different: `True`.

The first rid was still readable after the second crawl. Lookup by URL returns one copy, so a set of historical pages for selector checks still belongs in the repo mirror. Current docs keep stored pages for 30 days. Older material says 14.

## SDK methods that wrap the Storage API

Installed package: `crawlbase` 1.0.0. `StorageAPI` exposes `get`, `delete`, `bulk`, `rids`, and `totalCount`.
Live results:

- StorageClient.get_by_rid succeeded
- rids returned 5 ids
- totalCount=40
- bulk returned 1 pages, kind=html

`storage.py` calls those SDK methods. If a method raises, the client retries the same call over HTTP.

