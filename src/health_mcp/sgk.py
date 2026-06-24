"""Loader and query helpers for the bundled SGK EK-4/A drug snapshot.

The snapshot is a JSON file produced by ``scripts/build_sgk_snapshot.py`` from
the official SGK "Bedeli Ödenecek İlaçlar Listesi (EK-4/A)" Excel. At runtime
only the JSON is read — there is no Excel-parsing dependency.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "sgk_ek4a.json"


def _normalize(text: str) -> str:
    text = (text or "").upper().translate(str.maketrans("ÇĞİÖŞÜ", "CGIOSU"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_PATH.exists():
        return {"meta": {}, "drugs": []}
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def meta() -> dict:
    return _load().get("meta", {})


@lru_cache(maxsize=1)
def _indices() -> tuple[list[dict], dict[str, dict], dict[str, list[dict]]]:
    drugs = _load().get("drugs", [])
    by_barcode: dict[str, dict] = {}
    by_group: dict[str, list[dict]] = {}
    for drug in drugs:
        barcode = str(drug.get("barcode", "")).strip()
        if barcode:
            by_barcode[barcode] = drug
        group = drug.get("equivalent_group")
        if group:
            by_group.setdefault(group, []).append(drug)
    return drugs, by_barcode, by_group


def find_by_barcode(barcode: str) -> dict | None:
    _, by_barcode, _ = _indices()
    return by_barcode.get(str(barcode).strip())


def search_by_name(query: str, limit: int = 10) -> list[dict]:
    drugs, _, _ = _indices()
    normalized = _normalize(query)
    if not normalized:
        return []
    scored: list[tuple[int, int, dict]] = []
    for drug in drugs:
        name = _normalize(drug.get("name", ""))
        if normalized in name:
            scored.append((0 if name.startswith(normalized) else 1, len(name), drug))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [drug for *_, drug in scored[:limit]]


def group_members(group: str) -> list[dict]:
    _, _, by_group = _indices()
    return by_group.get(group, [])


def resolve(query: str) -> dict | None:
    """Resolve a query (barcode or drug name) to a single record."""
    text = str(query).strip()
    if text.isdigit():
        record = find_by_barcode(text)
        if record:
            return record
    matches = search_by_name(text, limit=1)
    return matches[0] if matches else None
