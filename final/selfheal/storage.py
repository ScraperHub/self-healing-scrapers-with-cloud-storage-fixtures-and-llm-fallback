"""Typed wrapper around the crawlbase StorageAPI SDK."""

from __future__ import annotations

import base64
import gzip
import json
from dataclasses import dataclass
from typing import Any, Protocol, cast

from selfheal.crawl import body_kind


class StorageError(RuntimeError):
    pass


@dataclass
class StoredPage:
    rid: str | None
    url: str | None
    body: str
    kind: str
    original_status: int | None
    cb_status: int | None
    stored_at: str | None


class StorageBackend(Protocol):
    def get(self, url_or_rid: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch one stored document."""

    def rids(self, limit: int = -1) -> dict[str, Any]:
        """List request ids."""

    def totalCount(self) -> int:
        """Return how many documents are stored."""

    def bulk(self, rids: list[str]) -> dict[str, Any]:
        """Fetch several documents."""


def sdk_backend(token: str) -> StorageBackend:
    from crawlbase import StorageAPI

    backend = StorageAPI({"token": token})
    return cast(StorageBackend, backend)


def decode_bulk_body(payload: str) -> str:
    raw = base64.b64decode(payload)
    try:
        raw = gzip.decompress(raw)
    except gzip.BadGzipFile:
        pass
    return raw.decode("utf-8", errors="replace")


def _as_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return ""


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if value in {"", "None"}:
        return None
    return value


class StorageClient:
    def __init__(self, token: str, backend: StorageBackend | None = None) -> None:
        if not token and backend is None:
            raise StorageError("CRAWLBASE_TOKEN is empty")
        self._backend = backend or sdk_backend(token)
        self._http = HttpStorageBackend(token) if backend is None and token else None

    def get_by_rid(self, rid: str) -> StoredPage:
        return self._get(rid)

    def latest_by_url(self, url: str) -> StoredPage:
        return self._get(url)

    def _invoke(self, name: str, *args: Any, **kwargs: Any) -> Any:
        try:
            return getattr(self._backend, name)(*args, **kwargs)
        except Exception as exc:
            if self._http is None:
                raise StorageError(str(exc)) from exc
            return getattr(self._http, name)(*args, **kwargs)

    def _get(self, url_or_rid: str) -> StoredPage:
        response = self._invoke("get", url_or_rid, {"format": "json"})
        if not isinstance(response, dict):
            raise StorageError("Storage get returned an unexpected payload")
        return parse_storage_response(response)

    def list_rids(self, limit: int = 20) -> list[str]:
        payload = self._invoke("rids", limit)
        rids = payload.get("rids", []) if isinstance(payload, dict) else []
        if not isinstance(rids, list):
            return []
        return [item for item in rids if isinstance(item, str)]

    def total_count(self) -> int:
        return int(self._invoke("totalCount"))

    def bulk(self, rids: list[str]) -> list[StoredPage]:
        response = self._invoke("bulk", rids)
        if not isinstance(response, dict):
            raise StorageError("Storage bulk returned an unexpected payload")
        return parse_bulk_response(response)


def parse_storage_response(response: dict[str, Any]) -> StoredPage:
    status = _as_int(response.get("status_code"))
    if status not in (None, 200):
        raise StorageError(f"Storage get failed with HTTP {status}")

    headers = response.get("headers") if isinstance(response.get("headers"), dict) else {}
    envelope = response.get("json_body")
    if envelope is None:
        envelope = response.get("json")

    body = ""
    rid = _clean(headers.get("rid")) if isinstance(headers, dict) else None
    url = _clean(headers.get("url")) if isinstance(headers, dict) else None
    stored_at = _clean(headers.get("stored_at")) if isinstance(headers, dict) else None
    original = _as_int(headers.get("original_status")) if isinstance(headers, dict) else None
    cb_status = _as_int(headers.get("cb_status")) if isinstance(headers, dict) else None
    if cb_status is None and isinstance(headers, dict):
        cb_status = _as_int(headers.get("pc_status"))

    if isinstance(envelope, str) and envelope.strip():
        body = envelope
    elif isinstance(envelope, dict):
        rid = rid or _clean(envelope.get("rid"))
        url = url or _clean(envelope.get("url"))
        stored_at = stored_at or _clean(envelope.get("stored_at"))
        original = original if original is not None else _as_int(envelope.get("original_status"))
        if cb_status is None:
            cb_status = _as_int(envelope.get("cb_status") or envelope.get("pc_status"))
        inner = envelope.get("body", envelope.get("original_body"))
        if isinstance(inner, str) and _looks_encoded(inner) and "stored_at" in envelope:
            body = decode_bulk_body(inner)
        elif isinstance(inner, str):
            body = inner
        elif isinstance(inner, (dict, list)):
            body = json.dumps(inner)
        elif "original_status" not in envelope and "body" not in envelope:
            body = json.dumps(envelope)
    else:
        body = _as_text(response.get("body"))

    return StoredPage(
        rid=rid,
        url=url,
        body=body,
        kind=body_kind(body),
        original_status=original,
        cb_status=cb_status,
        stored_at=stored_at,
    )


def _looks_encoded(value: str) -> bool:
    if len(value) < 16 or " " in value or value.startswith("<") or value.startswith("{"):
        return False
    alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n")
    return set(value[:80]).issubset(alphabet)


def parse_bulk_response(response: dict[str, Any]) -> list[StoredPage]:
    payload = response.get("json")
    if payload is None and isinstance(response.get("body"), (str, bytes)):
        text = _as_text(response.get("body"))
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict) and "body" in payload and isinstance(payload["body"], list):
        payload = payload["body"]
    if not isinstance(payload, list):
        raise StorageError("Storage bulk response was not a list")
    pages: list[StoredPage] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_body = item.get("body", "")
        if isinstance(raw_body, str) and raw_body and not raw_body.lstrip().startswith("<"):
            try:
                text = decode_bulk_body(raw_body)
            except Exception:
                text = raw_body
        elif isinstance(raw_body, str):
            text = raw_body
        else:
            text = json.dumps(raw_body)
        pages.append(
            StoredPage(
                rid=_clean(item.get("rid")),
                url=_clean(item.get("url")),
                body=text,
                kind=body_kind(text),
                original_status=_as_int(item.get("original_status")),
                cb_status=_as_int(item.get("cb_status") or item.get("pc_status")),
                stored_at=_clean(item.get("stored_at")),
            )
        )
    return pages


class HttpStorageBackend:
    """Raw Storage API client used when the SDK cannot parse a response."""

    def __init__(self, token: str, timeout: float = 60) -> None:
        if not token:
            raise StorageError("CRAWLBASE_TOKEN is empty")
        self._token = token
        self._timeout = timeout

    def get(self, url_or_rid: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, str] = {}
        if url_or_rid.startswith("http://") or url_or_rid.startswith("https://"):
            params["url"] = url_or_rid
        else:
            params["rid"] = url_or_rid
        for key, value in (options or {}).items():
            params[key] = str(value)
        return self._request("storage", params)

    def rids(self, limit: int = -1) -> dict[str, Any]:
        params = {"limit": str(limit)} if limit >= 0 else {}
        payload = self._request("storage/rids", params)
        body = payload.get("json")
        return body if isinstance(body, dict) else {"rids": []}

    def totalCount(self) -> int:
        payload = self._request("storage/total_count", {})
        body = payload.get("json")
        if isinstance(body, dict) and isinstance(body.get("totalCount"), int):
            return int(body["totalCount"])
        raise StorageError("Storage total_count was not a number")

    def bulk(self, rids: list[str]) -> dict[str, Any]:
        return self._request(
            "storage/bulk", {}, method="POST", data=json.dumps({"rids": rids}).encode("utf-8")
        )

    def _request(
        self,
        path: str,
        params: dict[str, str],
        method: str | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]:
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        from selfheal.crawl import decode_body

        query = {"token": self._token, **params}
        request = Request(
            "https://api.crawlbase.com/" + path + "?" + urlencode(query),
            data=data,
            headers={"Accept-Encoding": "gzip", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = response.read()
                headers = {key.lower(): value for key, value in response.headers.items()}
                status = int(response.status)
        except HTTPError as error:
            payload = error.read() or b""
            header_items = error.headers.items() if error.headers is not None else []
            headers = {key.lower(): value for key, value in header_items}
            status = int(error.code)
        except URLError as error:
            raise StorageError(f"Storage request failed: {error.reason}") from None
        text = decode_body(payload, headers)
        parsed: Any
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        return {"status_code": status, "headers": headers, "body": text, "json": parsed}
