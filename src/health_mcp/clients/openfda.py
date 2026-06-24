"""Client for the openFDA drug APIs (https://open.fda.gov/apis/).

No API key is required for basic use. Set ``OPENFDA_API_KEY`` to raise the
rate limits.
"""
from __future__ import annotations

import os

from .http import get_json

BASE = "https://api.fda.gov"


def _with_key(params: dict) -> dict:
    key = os.getenv("OPENFDA_API_KEY")
    if key:
        return {**params, "api_key": key}
    return params


async def drug_label(drug_name: str, limit: int = 1) -> list[dict]:
    """Return drug label documents matching a brand/generic/substance name."""
    search = (
        f'(openfda.brand_name:"{drug_name}"'
        f' OR openfda.generic_name:"{drug_name}"'
        f' OR openfda.substance_name:"{drug_name}")'
    )
    params = _with_key({"search": search, "limit": limit})
    data = await get_json(f"{BASE}/drug/label.json", params)
    return data.get("results", [])


async def adverse_event_counts(drug_name: str, limit: int = 10) -> list[dict]:
    """Return the most frequently reported adverse reactions (FAERS)."""
    search = (
        f'(patient.drug.openfda.brand_name:"{drug_name}"'
        f' OR patient.drug.openfda.generic_name:"{drug_name}"'
        f' OR patient.drug.medicinalproduct:"{drug_name}")'
    )
    params = _with_key(
        {
            "search": search,
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": limit,
        }
    )
    data = await get_json(f"{BASE}/drug/event.json", params)
    return data.get("results", [])


async def enforcement_reports(query: str, limit: int = 10) -> list[dict]:
    """Return drug recall / enforcement reports matching a product name."""
    params = _with_key({"search": f'product_description:"{query}"', "limit": limit})
    data = await get_json(f"{BASE}/drug/enforcement.json", params)
    return data.get("results", [])


async def drugs_for_indication(condition: str, limit: int = 10) -> list[dict]:
    """Return generic drug names whose labels list a given indication."""
    params = _with_key(
        {
            "search": f'indications_and_usage:"{condition}"',
            "count": "openfda.generic_name.exact",
            "limit": limit,
        }
    )
    data = await get_json(f"{BASE}/drug/label.json", params)
    return data.get("results", [])
