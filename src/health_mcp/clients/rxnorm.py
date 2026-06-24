"""Client for the NLM RxNorm / RxNav REST API.

Docs: https://rxnav.nlm.nih.gov/RxNormAPIs.html  (free, no key required)
"""
from __future__ import annotations

from .http import get_json

BASE = "https://rxnav.nlm.nih.gov/REST"


async def approximate_term(term: str, max_entries: int = 10) -> list[dict]:
    """Fuzzy-match a (possibly misspelled) term to RxNorm candidates."""
    params = {"term": term, "maxEntries": max_entries}
    data = await get_json(f"{BASE}/approximateTerm.json", params)
    if not data:
        return []
    return data.get("approximateGroup", {}).get("candidate", [])


async def rxcui_by_name(name: str) -> list[str]:
    """Return RxCUI identifiers for an exact drug name."""
    data = await get_json(f"{BASE}/rxcui.json", {"name": name})
    if not data:
        return []
    return data.get("idGroup", {}).get("rxnormId", [])


async def properties(rxcui: str) -> dict:
    """Return the RxNorm concept properties (name, tty, ...) for an RxCUI."""
    data = await get_json(f"{BASE}/rxcui/{rxcui}/properties.json")
    if not data:
        return {}
    return data.get("properties", {})


async def related(rxcui: str, ttys: list[str]) -> dict:
    """Return related concepts (by term type) for an RxCUI."""
    params = {"tty": " ".join(ttys)}
    data = await get_json(f"{BASE}/rxcui/{rxcui}/related.json", params)
    if not data:
        return {}
    return data.get("relatedGroup", {})


RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"


async def classes_by_rxcui(rxcui: str) -> list[dict]:
    """Return the drug-class memberships for an RxCUI (RxClass)."""
    data = await get_json(f"{RXCLASS_BASE}/class/byRxcui.json", {"rxcui": rxcui})
    if not data:
        return []
    return data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
