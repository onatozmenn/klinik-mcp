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


def test_count_reports_the_real_total_not_the_shown_slice():
    assert server._count(40, 25) == "**40** ürün (ilk 25 gösteriliyor)"
    assert server._count(3, 3) == "**3** ürün"
    assert server._count(9, 5, "kayıt") == "**9** kayıt (ilk 5 gösteriliyor)"


def test_pediatric_dose_rejects_nonpositive_cap():
    assert server.pediatric_dose(20, 50, 2, 0).startswith("Geçersiz girdi")
    assert server.pediatric_dose(20, 50, 2, -10).startswith("Geçersiz girdi")


def test_pediatric_dose_applies_cap():
    out = server.pediatric_dose(20, 50, 2, 800)
    assert "800.0 mg/gün" in out
    assert "400.0 mg" in out
