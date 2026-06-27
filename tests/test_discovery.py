"""Tests for registry-discovery artifacts (glama.json + MCP server card)."""
import asyncio
import json
from pathlib import Path

from health_mcp import server

ROOT = Path(__file__).resolve().parent.parent


def test_glama_json_is_valid_and_has_maintainers():
    data = json.loads((ROOT / "glama.json").read_text(encoding="utf-8"))
    assert isinstance(data.get("maintainers"), list)
    assert all(isinstance(name, str) and name for name in data["maintainers"])
    assert data["maintainers"]


def test_server_card_handler_returns_valid_card():
    response = asyncio.run(server._server_card(None))
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["serverInfo"]["name"] == "Klinik MCP"
    assert body["authentication"]["required"] is False


def test_health_endpoint_returns_ok():
    response = asyncio.run(server._health(None))
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["status"] == "ok"
    assert body["tool_count"] == 15


def test_prompts_registered():
    names = {p.name for p in asyncio.run(server.mcp.list_prompts())}
    assert {"ilac_bilgisi", "muadil_ve_geri_odeme", "renal_doz_kontrol"} <= names


def test_resources_registered():
    uris = {str(r.uri) for r in asyncio.run(server.mcp.list_resources())}
    assert {"info://server", "info://kaynaklar", "info://surumler"} <= uris
