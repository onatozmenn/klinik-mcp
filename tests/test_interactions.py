"""Tests for the DDInter interaction loader (interactions.py) and bridge."""
from health_mcp import interactions


def test_normalize_folds_turkish():
    assert interactions._normalize("İlaç Çöğüş") == "ILAC COGUS"


def test_snapshot_loaded_with_pairs():
    assert interactions.available()
    assert interactions.meta().get("pair_count", 0) > 0


def test_resolve_direct():
    assert interactions.resolve("Warfarin")["name"] == "Warfarin"


def test_resolve_english_alias():
    # DDInter uses the INN, not the US/common name.
    assert interactions.resolve("aspirin")["name"] == "Acetylsalicylic acid"
    assert interactions.resolve("paracetamol")["name"] == "Acetaminophen"


def test_resolve_turkish_spelling_alias():
    assert interactions.resolve("varfarin")["name"] == "Warfarin"


def test_titck_brand_bridge():
    # Turkish brand → single-substance ATC name → DDInter (combinations skipped).
    res = interactions.resolve("parol")
    assert res is not None
    assert res["name"] == "Acetaminophen"
    assert res["via"] == "titck"


def test_resolve_unknown_returns_none():
    assert interactions.resolve("zzz nonexistent drug 999") is None
    assert interactions.resolve("") is None


def test_known_major_pair():
    res = interactions.check_pair("Warfarin", "aspirin")
    assert res["level_label"] == "Major"


def test_same_substance_flagged():
    res = interactions.check_pair("Warfarin", "varfarin")
    assert res.get("same") is True
    assert res["level_label"] is None


def test_unresolved_pair_reports_none():
    res = interactions.check_pair("Warfarin", "zzz nonexistent drug 999")
    assert res["b"] is None
    assert res["level_label"] is None
