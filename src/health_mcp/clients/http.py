"""Shared async HTTP helper for upstream health APIs."""
from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 20.0
USER_AGENT = "klinik-mcp/0.1 (+https://huggingface.co/spaces/onatozmenn/klinik-mcp)"

_LIMITS = httpx.Limits(max_keepalive_connections=10, max_connections=20)
_client: httpx.AsyncClient | None = None


class APIError(Exception):
    """Raised when an upstream API request fails."""


def _get_client() -> httpx.AsyncClient:
    """Return a lazily-created, shared client so connections are pooled/reused."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            limits=_LIMITS,
        )
    return _client


async def aclose() -> None:
    """Close the shared client (call on shutdown for a clean exit)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def get_json(
    url: str,
    params: dict | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET a URL and return parsed JSON.

    Reuses a shared, connection-pooled client. Returns an empty dict on HTTP
    404 (used by openFDA to signal "no match"), and raises :class:`APIError`
    for any other failure.
    """
    try:
        response = await _get_client().get(url, params=params, timeout=timeout)
    except httpx.HTTPError as exc:
        raise APIError(f"Request to {url} failed: {exc}") from exc

    if response.status_code == 404:
        return {}
    if response.status_code >= 400:
        raise APIError(
            f"{url} returned HTTP {response.status_code}: {response.text[:200]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise APIError(f"Invalid JSON from {url}: {exc}") from exc
