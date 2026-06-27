"""Tests for the TİTCK KÜB/KT client parsing helpers (no network)."""
from health_mcp.clients import kubkt


def test_first_pdf_extracts_href():
    cell = (
        '<div class="cell text-center">'
        '<a href="https://titck.gov.tr/storage/kubKtAttachments/abc.pdf">PDF</a></div>'
    )
    assert (
        kubkt._first_pdf(cell)
        == "https://titck.gov.tr/storage/kubKtAttachments/abc.pdf"
    )
    assert kubkt._first_pdf("") is None
    assert kubkt._first_pdf(None) is None
    assert kubkt._first_pdf("<span>yok</span>") is None


def test_first_pdf_encodes_spaces():
    cell = '<a href="https://x/parol 10 MG kub.pdf">PDF</a>'
    assert kubkt._first_pdf(cell) == "https://x/parol%2010%20MG%20kub.pdf"


def test_parse_row_normalizes_fields():
    row = {
        "name": "PAROL 500 MG TABLET",
        "element": "PARASETAMOL",
        "firmName": "ATABAY",
        "documentPathKub": '<a href="https://x/kub.pdf">PDF</a>',
        "documentPathKt": '<a href="https://x/kt.pdf">PDF</a>',
    }
    parsed = kubkt._parse_row(row)
    assert parsed["name"] == "PAROL 500 MG TABLET"
    assert parsed["active"] == "PARASETAMOL"
    assert parsed["kub_url"] == "https://x/kub.pdf"
    assert parsed["kt_url"] == "https://x/kt.pdf"


def test_build_form_includes_columns_and_token():
    form = kubkt._build_form("TOKEN", "parol", 5)
    assert form["_token"] == "TOKEN"
    assert form["search[value]"] == "parol"
    assert form["length"] == "5"
    assert form["columns[0][data]"] == "name"
    assert form["columns[6][data]"] == "documentPathKt"
