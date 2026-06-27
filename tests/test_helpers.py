"""Tests for server-side formatting/sanitization helpers (server.py)."""
from health_mcp import server


def test_clean_strips_query_breaking_chars():
    assert server._clean('aspirin"') == "aspirin"
    assert server._clean("a\\b") == "a b"
    assert server._clean("  amoxicillin  ") == "amoxicillin"


def test_join_handles_list_scalar_and_none():
    assert server._join(["a", "b", None, "c"]) == "a b c"
    assert server._join("x") == "x"
    assert server._join(None) == ""


def test_truncate_appends_ellipsis_only_when_needed():
    assert server._truncate("short", 10) == "short"
    out = server._truncate("x" * 100, 10)
    assert out.endswith("…")
    assert len(out) <= 12


def test_fmt_date():
    assert server._fmt_date("20260624") == "2026-06-24"
    assert server._fmt_date(None) == "?"
    assert server._fmt_date("notadate") == "notadate"
