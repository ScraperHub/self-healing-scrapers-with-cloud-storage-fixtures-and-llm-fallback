"""Crawling API client. Tokens stay in the environment."""

from __future__ import annotations

import gzip
import json
import ssl
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

CRAWLBASE_ENDPOINT = "https://api.crawlbase.com/"


class CrawlError(RuntimeError):
    def __init__(self, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


@dataclass
class PageFetch:
    requested_url: str
    body: str
    http_status: int
    original_status: int | None
    cb_status: int | None
    rid: str | None
    final_url: str | None
    content_type: str

    @property
    def ok(self) -> bool:
        return self.cb_status == 200 and self.original_status == 200


class Opener(Protocol):
    def __call__(
        self, token: str, target: str, params: dict[str, str], timeout: float
    ) -> tuple[int, dict[str, str], bytes]:
        """Return HTTP status, lower-cased headers, and the raw body."""


def _header_int(headers: dict[str, str], *names: str) -> int | None:
    for name in names:
        raw = headers.get(name.lower())
        if raw is None or raw in {"", "None"}:
            continue
        try:
            return int(raw)
        except ValueError:
            continue
    return None


def rid_from_headers(headers: dict[str, str]) -> str | None:
    direct = _header_str(headers, "rid")
    if direct:
        return direct
    storage_url = headers.get("storage_url")
    if not storage_url:
        return None
    values = parse_qs(urlparse(storage_url).query).get("rid") or []
    if values and values[0] and values[0] != "None":
        return values[0]
    return None


def _header_str(headers: dict[str, str], *names: str) -> str | None:
    for name in names:
        raw = headers.get(name.lower())
        if raw and raw != "None":
            return raw
    return None


def decode_body(payload: bytes, headers: dict[str, str]) -> str:
    data = payload
    if headers.get("content-encoding") == "gzip":
        data = gzip.decompress(payload)
    return data.decode("utf-8", errors="replace")


def body_kind(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    if stripped.startswith("<"):
        return "html"
    return "text"


def urllib_opener(
    token: str, target: str, params: dict[str, str], timeout: float
) -> tuple[int, dict[str, str], bytes]:
    query = {"token": token, "url": target, **params}
    # The token is in the query. Error messages below must not include this URL.
    request = Request(
        CRAWLBASE_ENDPOINT + "?" + urlencode(query),
        headers={"Accept-Encoding": "gzip"},
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            payload = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
            return int(response.status), headers, payload
    except HTTPError as error:
        payload = error.read() or b""
        header_items = error.headers.items() if error.headers is not None else []
        headers = {key.lower(): value for key, value in header_items}
        return int(error.code), headers, payload
    except URLError as error:
        reason = getattr(error, "reason", "request failed")
        raise CrawlError(f"Crawlbase request failed: {reason}") from None
    except TimeoutError as error:
        raise CrawlError("Crawlbase request timed out") from error


def _stringify(options: dict[str, object]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for key, value in options.items():
        if value is None:
            continue
        if isinstance(value, bool):
            rendered[key] = "true" if value else "false"
        else:
            rendered[key] = str(value)
    return rendered


def is_block_page(page: PageFetch) -> bool:
    url = (page.final_url or "").lower()
    return "checkpoint" in url or "captcha" in url


class CrawlbaseClient:
    def __init__(
        self,
        token: str,
        js_token: str | None = None,
        opener: Opener | None = None,
        timeout: float = 90,
    ) -> None:
        if not token:
            raise CrawlError("CRAWLBASE_TOKEN is empty")
        self.token = token
        self.js_token = js_token
        self._opener = opener or urllib_opener
        self.timeout = timeout

    def fetch(self, url: str, use_js: bool = False, **options: object) -> PageFetch:
        token = self.js_token if use_js else self.token
        if use_js and not token:
            raise CrawlError("CRAWLBASE_JS_TOKEN is empty")
        page = self._once(token or self.token, url, options)
        blocked = page.cb_status == 503 or is_block_page(page)
        if blocked and not use_js and self.js_token:
            return self._once(self.js_token, url, options)
        return page

    def _once(self, token: str, url: str, options: dict[str, object]) -> PageFetch:
        try:
            status, headers, payload = self._opener(token, url, _stringify(options), self.timeout)
        except CrawlError:
            raise
        except Exception as error:
            raise CrawlError(f"Crawlbase request failed: {type(error).__name__}") from None
        return parse_fetch(url, status, headers, payload)


def parse_fetch(url: str, http_status: int, headers: dict[str, str], payload: bytes) -> PageFetch:
    text = decode_body(payload, headers)
    original = _header_int(headers, "original_status")
    cb_status = _header_int(headers, "cb_status", "pc_status")
    rid = rid_from_headers(headers)
    final_url = _header_str(headers, "url")
    content_type = headers.get("content-type", "")

    if body_kind(text) == "json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            original = (
                original if original is not None else _maybe_int(parsed.get("original_status"))
            )
            envelope_cb = _maybe_int(parsed.get("cb_status"))
            if envelope_cb is None:
                envelope_cb = _maybe_int(parsed.get("pc_status"))
            cb_status = cb_status if cb_status is not None else envelope_cb
            if rid is None and isinstance(parsed.get("rid"), str):
                rid = parsed["rid"]
            if rid is None and isinstance(parsed.get("storage_url"), str):
                rid = rid_from_headers({"storage_url": parsed["storage_url"]})
            if final_url is None and isinstance(parsed.get("url"), str):
                final_url = parsed["url"]
            inner = parsed.get("body")
            # format=json wraps the page. A scraper body is itself the product JSON.
            if "original_status" in parsed and inner is not None:
                text = inner if isinstance(inner, str) else json.dumps(inner)

    return PageFetch(
        requested_url=url,
        body=text,
        http_status=http_status,
        original_status=original,
        cb_status=cb_status,
        rid=rid,
        final_url=final_url,
        content_type=content_type,
    )


def _maybe_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def loads_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None
