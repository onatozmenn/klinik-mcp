"""Client for TİTCK's KÜB/KT (SmPC / patient leaflet) search endpoint.

The official list at https://www.titck.gov.tr/kubkt is a server-side DataTable
backed by a POST endpoint that returns, per product, the official **KÜB** (Kısa
Ürün Bilgisi — for clinicians) and **KT** (Kullanma Talimatı — for patients) PDF
links. We query it live (no API key) and return the official PDF URLs.
"""
from __future__ import annotations

import re

import httpx

from .http import DEFAULT_TIMEOUT, USER_AGENT, APIError

PAGE = "https://www.titck.gov.tr/kubkt"
ENDPOINT = "https://www.titck.gov.tr/getkubktviewdatatable"
_COLUMNS = (
    "name",
    "element",
    "firmName",
    "confirmationDateKub",
    "confirmationDateKt",
    "documentPathKub",
    "documentPathKt",
)
_TOKEN_RE = re.compile(r'_token:\s*"([^"]+)"')
_PDF_RE = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


def _first_pdf(html: str | None) -> str | None:
    """Extract the first PDF href from a DataTables document cell.

    TİTCK file URLs may contain literal spaces, so encode them for valid links.
    """
    if not html:
        return None
    match = _PDF_RE.search(str(html))
    return match.group(1).replace(" ", "%20") if match else None


def _parse_row(row: dict) -> dict:
    """Normalize one raw KÜB/KT row into name/active/company + PDF links."""
    return {
        "name": " ".join(str(row.get("name", "")).split()),
        "active": " ".join(str(row.get("element", "")).split()),
        "company": " ".join(str(row.get("firmName", "")).split()),
        "kub_url": _first_pdf(row.get("documentPathKub")),
        "kt_url": _first_pdf(row.get("documentPathKt")),
    }


def _build_form(token: str, query: str, limit: int) -> dict:
    form = {
        "_token": token,
        "draw": "1",
        "start": "0",
        "length": str(limit),
        "search[value]": query,
        "search[regex]": "false",
        "order[0][column]": "0",
        "order[0][dir]": "asc",
    }
    for index, column in enumerate(_COLUMNS):
        form[f"columns[{index}][data]"] = column
        form[f"columns[{index}][name]"] = ""
        form[f"columns[{index}][searchable]"] = "true"
        form[f"columns[{index}][orderable]"] = "true"
        form[f"columns[{index}][search][value]"] = ""
        form[f"columns[{index}][search][regex]"] = "false"
    return form


async def search_leaflets(query: str, limit: int = 5) -> list[dict]:
    """Search TİTCK KÜB/KT by drug name; return rows with KÜB & KT PDF links."""
    headers = {"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest"}
    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT, headers=headers, follow_redirects=True
        ) as client:
            page = await client.get(PAGE)
            token_match = _TOKEN_RE.search(page.text)
            if not token_match:
                raise APIError("KÜB/KT oturum belirteci bulunamadı")
            response = await client.post(
                ENDPOINT, data=_build_form(token_match.group(1), query, limit)
            )
    except httpx.HTTPError as exc:
        raise APIError(f"KÜB/KT isteği başarısız: {exc}") from exc
    if response.status_code >= 400:
        raise APIError(f"KÜB/KT HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise APIError(f"KÜB/KT geçersiz yanıt: {exc}") from exc
    return [_parse_row(row) for row in payload.get("data", [])]
