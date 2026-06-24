"""Shared async HTTP helper for upstream health APIs."""
from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 20.0
USER_AGENT = "health-mcp/0.1 (+https://github.com/openthing/health-mcp)"


class APIError(Exception):
    """Raised when an upstream API request fails."""


async def get_json(
    url: str,
    params: dict | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET a URL and return parsed JSON.

    Returns an empty dict on HTTP 404 (used by openFDA to signal "no match"),
    and raises :class:`APIError` for any other failure.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            response = await client.get(url, params=params)
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
