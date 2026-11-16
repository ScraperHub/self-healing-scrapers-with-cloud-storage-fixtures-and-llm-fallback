"""store=true crawl. The rid is a query parameter on storage_url."""

from __future__ import annotations

import gzip
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


def crawl_store(token: str, page_url: str, timeout: float = 90) -> str:
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
    if rid is None and headers.get("rid") not in (None, "", "None"):
        direct = headers.get("rid")
        rid = direct if isinstance(direct, str) else None
    if rid is None:
        rid = _rid_from_body(payload)
    if not rid:
        raise RuntimeError("store=true response had no rid")
    return rid


def _rid_from_body(payload: bytes) -> str | None:
    text = payload.decode("utf-8", errors="replace").lstrip()
    if not text.startswith("{"):
        return None
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        return None
    storage_url = parsed.get("storage_url")
    if isinstance(storage_url, str):
        return _rid_from_storage_url(storage_url)
    rid = parsed.get("rid")
    if isinstance(rid, str) and rid and rid != "None":
        return rid
    return None


def _rid_from_storage_url(storage_url: str | None) -> str | None:
    if not storage_url:
        return None
    values = parse_qs(urlparse(storage_url).query).get("rid") or []
    rid = values[0] if values else ""
    if not rid or rid == "None":
        return None
    return rid
