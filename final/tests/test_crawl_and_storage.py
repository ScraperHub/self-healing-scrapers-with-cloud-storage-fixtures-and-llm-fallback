from __future__ import annotations

import base64
import gzip
import json

import pytest
from selfheal.crawl import CrawlbaseClient, CrawlError, body_kind, decode_body, parse_fetch
from selfheal.storage import (
    HttpStorageBackend,
    StorageClient,
    StorageError,
    decode_bulk_body,
    parse_bulk_response,
    parse_storage_response,
)


def test_parse_fetch_reads_rid_from_storage_url() -> None:
    page = parse_fetch(
        "https://example.com",
        200,
        {
            "cb_status": "200",
            "original_status": "200",
            "content-type": "text/html",
            "storage_url": "https://api.crawlbase.com/storage?token=fake&rid=abc123",
        },
        b"<html>Example Domain</html>",
    )
    assert page.rid == "abc123"
    envelope = {
        "original_status": 200,
        "cb_status": 200,
        "rid": "RID123",
        "url": "https://example.com/final",
        "body": "<html>ok</html>",
    }
    page = parse_fetch(
        "https://example.com",
        200,
        {"content-type": "application/json"},
        json.dumps(envelope).encode("utf-8"),
    )
    assert page.rid == "RID123"
    assert page.body == "<html>ok</html>"
    assert page.original_status == 200
    assert page.cb_status == 200
    assert page.final_url == "https://example.com/final"
    assert body_kind(page.body) == "html"


def test_parse_fetch_prefers_headers_and_gunzips() -> None:
    payload = gzip.compress(b'{"name": "Shoe"}')
    page = parse_fetch(
        "https://www.amazon.com/dp/x",
        200,
        {
            "content-encoding": "gzip",
            "content-type": "application/json",
            "original_status": "200",
            "pc_status": "200",
            "rid": "from-header",
        },
        payload,
    )
    assert page.rid == "from-header"
    assert page.cb_status == 200
    assert "Shoe" in page.body


def test_decode_body_plain() -> None:
    assert decode_body(b"hello", {}) == "hello"


def test_client_retries_with_the_js_token_after_503() -> None:
    calls: list[str] = []

    def opener(token: str, target: str, params: dict[str, str], timeout: float):
        calls.append(token)
        status = "503" if token == "normal" else "200"
        body = b"<html>blocked</html>" if token == "normal" else b"<html>ok</html>"
        headers = {"cb_status": status, "original_status": "200", "content-type": "text/html"}
        return 200, headers, body

    client = CrawlbaseClient("normal", js_token="js", opener=opener)
    page = client.fetch("https://www.walmart.com/ip/1")
    assert calls == ["normal", "js"]
    assert page.cb_status == 200
    assert "ok" in page.body


def test_client_does_not_retry_without_a_js_token() -> None:
    def opener(token: str, target: str, params: dict[str, str], timeout: float):
        return 200, {"cb_status": "503", "original_status": "200"}, b"blocked"

    page = CrawlbaseClient("normal", opener=opener).fetch("https://example.com")
    assert page.cb_status == 503


def test_client_rejects_an_empty_token_and_hides_transport_urls() -> None:
    with pytest.raises(CrawlError):
        CrawlbaseClient("").fetch("https://example.com")

    def opener(token: str, target: str, params: dict[str, str], timeout: float):
        raise RuntimeError("https://api.crawlbase.com/?token=secret")

    with pytest.raises(CrawlError) as caught:
        CrawlbaseClient("normal", opener=opener).fetch("https://example.com")
    assert "secret" not in str(caught.value)


def test_storage_string_body_is_the_stored_page() -> None:
    page = parse_storage_response(
        {
            "status_code": 200,
            "headers": {"rid": "abc"},
            "json_body": "<!doctype html><html>Example Domain</html>",
            "body": '{"body": "<!doctype html><html>Example Domain</html>"}',
        }
    )
    assert page.kind == "html"
    assert "Example Domain" in page.body
    page = parse_storage_response(
        {
            "status_code": 200,
            "headers": {},
            "json_body": {
                "rid": "abc",
                "url": "https://example.com",
                "stored_at": "2026-11-16T00:00:00Z",
                "original_status": 200,
                "pc_status": 200,
                "body": "<html>stored</html>",
            },
        }
    )
    assert page.kind == "html"
    assert page.rid == "abc"
    assert page.cb_status == 200

    raw = gzip.compress(b"<html>bulk</html>")
    encoded = base64.b64encode(raw).decode("ascii")
    assert "bulk" in decode_bulk_body(encoded)
    pages = parse_bulk_response(
        {
            "json": [
                {
                    "rid": "b1",
                    "url": "https://example.com/a",
                    "original_status": 200,
                    "body": encoded,
                    "stored_at": "2026-11-16T00:00:00Z",
                }
            ]
        }
    )
    assert pages[0].body.startswith("<html>bulk")
    assert pages[0].kind == "html"


def test_storage_client_uses_the_injected_backend() -> None:
    class Backend:
        def get(self, url_or_rid: str, options: dict | None = None) -> dict:
            assert url_or_rid == "rid-1"
            return {
                "status_code": 200,
                "headers": {"rid": "rid-1"},
                "json": {"rid": "rid-1", "body": "<html>one</html>", "original_status": 200},
            }

        def rids(self, limit: int = -1) -> dict:
            return {"rids": ["rid-1", 3]}

        def totalCount(self) -> int:
            return 4

        def bulk(self, rids: list[str]) -> dict:
            return {"json": [{"rid": "rid-1", "body": "<html>one</html>", "original_status": 200}]}

    client = StorageClient("", backend=Backend())
    assert client.get_by_rid("rid-1").body.startswith("<html>")
    assert client.list_rids() == ["rid-1"]
    assert client.total_count() == 4
    assert client.bulk(["rid-1"])[0].rid == "rid-1"


def test_storage_errors() -> None:
    with pytest.raises(StorageError):
        StorageClient("")
    with pytest.raises(StorageError):
        parse_storage_response({"status_code": 404, "body": ""})
    with pytest.raises(StorageError):
        parse_bulk_response({"json": {"nope": True}})


def test_http_backend_builds_a_get_without_leaking_on_parse() -> None:
    # Construction only. The live suite exercises the network.
    backend = HttpStorageBackend("token")
    assert backend._token == "token"
