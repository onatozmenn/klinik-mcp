"""Tests for column auto-detection in scripts/build_prices.py."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_prices.py"


@pytest.fixture(scope="module")
def build_prices():
    spec = importlib.util.spec_from_file_location("build_prices", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_depot_column_with_kdv_is_not_misread_as_retail(build_prices):
    headers = ["Barkod", "Perakende Satış Fiyatı", "Depocu Satış Fiyatı (KDV'siz)"]
    mapping = build_prices.detect_columns(headers)
    assert mapping["barcode"] == 0
    assert mapping["retail"] == 1
    assert mapping["depot"] == 2


def test_detects_psf_and_dsf_short_forms(build_prices):
    headers = ["BARKOD", "DSF", "PSF"]
    mapping = build_prices.detect_columns(headers)
    assert mapping == {"barcode": 0, "depot": 1, "retail": 2}


def test_to_float_handles_turkish_decimal(build_prices):
    assert build_prices.to_float("1.234,56") == pytest.approx(1234.56)
    assert build_prices.to_float("18,50") == pytest.approx(18.50)
    assert build_prices.to_float("") is None
    assert build_prices.to_float(None) is None
