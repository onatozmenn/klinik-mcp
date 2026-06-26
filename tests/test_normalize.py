"""Tests for Turkish text normalization in the snapshot loaders."""
from health_mcp import sgk, titck


def test_sgk_normalize_folds_turkish_chars():
    assert sgk._normalize("İlaç Çöğüş") == "ILAC COGUS"
    assert sgk._normalize("  multiple   spaces ") == "MULTIPLE SPACES"
    assert sgk._normalize(None) == ""


def test_titck_normalize_matches_sgk():
    for text in ["Aspirin", "PAROL 500 MG", "İğne", "Çözelti"]:
        assert titck._normalize(text) == sgk._normalize(text)
