"""Client for the NCBI E-utilities (PubMed) API.

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/  (free; ``NCBI_API_KEY``
optional for higher rate limits)
"""
from __future__ import annotations

import os

from .http import get_json

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _with_key(params: dict) -> dict:
    key = os.getenv("NCBI_API_KEY")
    if key:
        return {**params, "api_key": key}
    return params


async def search(query: str, retmax: int = 10) -> list[str]:
    """Return PubMed IDs (PMIDs) matching a query, ordered by relevance."""
    params = _with_key(
        {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retmode": "json",
            "sort": "relevance",
        }
    )
    data = await get_json(f"{BASE}/esearch.fcgi", params)
    return data.get("esearchresult", {}).get("idlist", [])


async def summaries(pmids: list[str]) -> dict:
    """Return article summaries keyed by PMID for a list of PMIDs."""
    if not pmids:
        return {}
    params = _with_key({"db": "pubmed", "id": ",".join(pmids), "retmode": "json"})
    data = await get_json(f"{BASE}/esummary.fcgi", params)
    return data.get("result", {})
