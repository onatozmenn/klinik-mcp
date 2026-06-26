"""Contract tests for the fragile scraping regexes in scripts/update_data.py.

These guard against silent breakage of the patterns that locate the official
TİTCK / SGK download links.
"""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_data.py"


@pytest.fixture(scope="module")
def update_data():
    spec = importlib.util.spec_from_file_location("update_data", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skrs_xlsx_regex_matches_storage_link(update_data):
    html = (
        'href="https://titck.gov.tr/storage/Archive/2026/dynamicModul/'
        'skrserecete_2026.xlsx"'
    )
    assert update_data.SKRS_XLSX_RE.findall(html) == [
        "https://titck.gov.tr/storage/Archive/2026/dynamicModul/skrserecete_2026.xlsx"
    ]


def test_skrs_xlsx_regex_ignores_non_xlsx(update_data):
    html = 'href="https://titck.gov.tr/storage/other/document.pdf"'
    assert update_data.SKRS_XLSX_RE.findall(html) == []


def test_sgk_detail_regex_matches_islenmis_guncel(update_data):
    html = '<a href="/duyuru/detay/Islenmis-Guncel-SUT-2026">'
    assert update_data.SGK_DETAIL_RE.search(html) is not None


def test_sgk_zip_regex_matches_download_link(update_data):
    html = '<a href="/Download/DownloadFile?f=sut%2F2026%2Fpaket.zip">'
    match = update_data.SGK_ZIP_RE.search(html)
    assert match is not None
    assert ".zip" in match.group(0)


def test_titck_safety_xlsx_regex_matches_attachment(update_data):
    html = (
        'href="https://titck.gov.tr/storage/Archive/2025/'
        'dynamicModulesAttachment/ekizlemlistesi19.12.25_abc.xlsx"'
    )
    matches = update_data.TITCK_SAFETY_XLSX_RE.findall(html)
    assert matches and matches[0].endswith(".xlsx")


def test_titck_safety_xlsx_regex_ignores_non_attachment(update_data):
    html = 'href="https://titck.gov.tr/storage/other/document.xlsx"'
    assert update_data.TITCK_SAFETY_XLSX_RE.findall(html) == []
