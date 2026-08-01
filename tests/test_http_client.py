"""Tests for the shared, connection-pooled HTTP client (clients/http.py)."""
import asyncio

from health_mcp import __version__
from health_mcp.clients import http


def test_get_client_is_reused():
    http._client = None
    first = http._get_client()
    second = http._get_client()
    assert first is second
    assert not first.is_closed


def test_aclose_closes_and_resets_the_shared_client():
    client = http._get_client()
    asyncio.run(http.aclose())
    assert client.is_closed
    assert http._client is None


def test_user_agent_identifies_klinik_mcp():
    assert f"klinik-mcp/{__version__}" in http.USER_AGENT
    assert "huggingface.co/spaces/onatozmenn/klinik-mcp" in http.USER_AGENT
