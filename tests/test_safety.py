"""Tests for the TİTCK drug-safety loader (safety.py) against bundled data."""
from health_mcp import safety


def test_normalize_and_first_token():
    assert safety._normalize("İlaç Çöğüş") == "ILAC COGUS"
    assert safety._first_token("ORENCIA 250 MG IV") == "ORENCIA"
    assert safety._first_token("") == ""


def test_snapshot_loaded_with_records():
    assert safety.available()
    meta = safety.meta()
    assert meta["monitoring"]["count"] > 0
    assert meta["cancellations"]["count"] > 0


def test_monitoring_status_matches_a_real_entry():
    entry = safety._load()["monitoring"][0]
    found = safety.monitoring_status(name=entry["name"])
    assert found is not None
    assert found["active"] == entry["active"]


def test_monitoring_status_absent_returns_none():
    assert safety.monitoring_status(name="ZZZ NONEXISTENT DRUG 999") is None


def test_cancellation_status_matches_a_real_entry():
    entry = safety._load()["cancellations"][0]
    found = safety.cancellation_status(name=entry["name"])
    assert any(record["name"] == entry["name"] for record in found)


def test_cancellation_status_absent_returns_empty():
    assert safety.cancellation_status(name="ZZZ NONEXISTENT 999") == []
    assert safety.cancellation_status() == []
