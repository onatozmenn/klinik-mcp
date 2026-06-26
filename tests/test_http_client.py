"""Tests for the shared, connection-pooled HTTP client (clients/http.py)."""
from health_mcp.clients import http


def test_get_client_is_reused():
    http._client = None
    first = http._get_client()
    second = http._get_client()
    assert first is second
    assert not first.is_closed


def test_user_agent_identifies_klinik_mcp():
    assert "klinik-mcp" in http.USER_AGENT
    assert "huggingface.co/spaces/onatozmenn/klinik-mcp" in http.USER_AGENT
