"""Tests for the pure clinical formula helpers (clinical.py)."""
import pytest

from health_mcp import clinical


def test_cockcroft_gault_male_known_value():
    # (140-40)*80 / (72*1.0) = 8000/72 = 111.11
    crcl = clinical.cockcroft_gault(40, 80, 1.0, is_female=False)
    assert crcl == pytest.approx(111.11, abs=0.1)


def test_cockcroft_gault_female_applies_085_factor():
    male = clinical.cockcroft_gault(40, 80, 1.0, is_female=False)
    female = clinical.cockcroft_gault(40, 80, 1.0, is_female=True)
    assert female == pytest.approx(male * 0.85, abs=1e-9)


@pytest.mark.parametrize(
    "age,weight,scr",
    [(0, 80, 1.0), (40, 0, 1.0), (40, 80, 0.0), (-1, 80, 1.0)],
)
def test_cockcroft_gault_rejects_nonpositive(age, weight, scr):
    with pytest.raises(ValueError):
        clinical.cockcroft_gault(age, weight, scr, is_female=False)


@pytest.mark.parametrize(
    "crcl,expected",
    [
        (120, "normal"),
        (90, "normal"),
        (75, "hafif"),
        (45, "orta"),
        (20, "ciddi"),
        (5, "yetmezli"),
    ],
)
def test_renal_function_category_bands(crcl, expected):
    assert expected in clinical.renal_function_category(crcl).lower()


def test_mosteller_bsa_known_value():
    # sqrt(180*80 / 3600) = sqrt(4) = 2.0
    assert clinical.mosteller_bsa(180, 80) == pytest.approx(2.0, abs=1e-9)


@pytest.mark.parametrize("height,weight", [(0, 80), (180, 0), (-1, 80)])
def test_mosteller_bsa_rejects_nonpositive(height, weight):
    with pytest.raises(ValueError):
        clinical.mosteller_bsa(height, weight)
