"""Tests for the TİTCK foreign-supply loader (foreign.py) against bundled data."""
from health_mcp import foreign


def test_normalize_folds_turkish():
    assert foreign._normalize("İlaç Çöğüş") == "ILAC COGUS"


def test_snapshot_loaded_with_records():
    assert foreign.available()
    assert foreign.meta()["count"] > 0


def test_search_matches_a_real_entry():
    entry = foreign._load()["substances"][0]
    results = foreign.search_by_name(entry["active"])
    assert any(r["active"] == entry["active"] for r in results)


def test_find_by_atc_matches():
    entry = next(s for s in foreign._load()["substances"] if s.get("atc_code"))
    results = foreign.find_by_atc(entry["atc_code"])
    assert any(r["atc_code"] == entry["atc_code"] for r in results)


def test_search_absent_returns_empty():
    assert foreign.search_by_name("ZZZ NONEXISTENT 999") == []
    assert foreign.search_by_name("") == []
