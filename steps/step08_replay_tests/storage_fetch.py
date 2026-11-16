"""Read one stored document back by rid."""

from __future__ import annotations

import gzip
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


def store_page(token: str, page_url: str, timeout: float = 90) -> str:
    """store=true. The rid is the rid query parameter on storage_url."""

    params = urlencode({"token": token, "url": page_url, "store": "true"})
    request = Request(
        "https://api.crawlbase.com/?" + params,
        headers={"Accept-Encoding": "gzip"},
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            payload = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Crawlbase request failed: {type(exc).__name__}") from None
    if headers.get("content-encoding") == "gzip" or payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    rid = _rid_from_storage_url(headers.get("storage_url"))
    if not rid:
        text = payload.decode("utf-8", errors="replace").lstrip()
        if text.startswith("{"):
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("storage_url"), str):
                rid = _rid_from_storage_url(parsed["storage_url"])
    if not rid:
        raise RuntimeError("store=true response had no rid")
    return rid


def _rid_from_storage_url(storage_url: str | None) -> str | None:
    if not storage_url:
        return None
    values = parse_qs(urlparse(storage_url).query).get("rid") or []
    rid = values[0] if values else ""
    if not rid or rid == "None":
        return None
    return rid


def fetch_rid(token: str, rid: str) -> str:
    from crawlbase import StorageAPI

    api = StorageAPI({"token": token})
    response = api.get(rid, {"format": "json"})
    if not isinstance(response, dict):
        raise RuntimeError("storage get returned an unexpected payload")
    body = response.get("json_body")
    if isinstance(body, str) and body.strip():
        return body
    if isinstance(body, dict):
        inner = body.get("body")
        if isinstance(inner, str) and inner.strip():
            return inner
    raw = response.get("body")
    if isinstance(raw, str) and raw.strip():
        return raw
    raise RuntimeError("storage get returned an empty body")
