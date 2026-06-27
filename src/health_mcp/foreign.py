"""Loader and query helpers for the bundled TİTCK 'Yurt Dışı Etkin Madde'
(foreign-supply active-substance) snapshot.

The snapshot (``data/titck_foreign.json``) is produced by
``scripts/build_titck_foreign_snapshot.py`` from TİTCK's official "Yurt Dışı
Etkin Madde Listesi" (dinamikmodul/126). At runtime only the JSON is read.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "titck_foreign.json"


def _normalize(text: str) -> str:
    text = (text or "").upper().translate(str.maketrans("ÇĞİÖŞÜ", "CGIOSU"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_PATH.exists():
        return {"meta": {}, "substances": []}
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def meta() -> dict:
    return _load().get("meta", {})


def available() -> bool:
    return bool(_load().get("substances"))


@lru_cache(maxsize=1)
def _by_atc() -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for substance in _load().get("substances", []):
        atc = str(substance.get("atc_code", "")).strip()
        if atc:
            index.setdefault(atc, []).append(substance)
    return index


def find_by_atc(atc: str) -> list[dict]:
    return _by_atc().get(str(atc).strip(), [])


def search_by_name(query: str, limit: int = 20) -> list[dict]:
    """Search the foreign-supply list by active substance or ATC name."""
    substances = _load().get("substances", [])
    normalized = _normalize(query)
    if not normalized:
        return []
    scored: list[tuple[int, int, dict]] = []
    for substance in substances:
        haystack = _normalize(
            f"{substance.get('active', '')} {substance.get('atc_name', '')}"
        )
        if normalized in haystack:
            scored.append(
                (0 if haystack.startswith(normalized) else 1, len(haystack), substance)
            )
    scored.sort(key=lambda item: (item[0], item[1]))
    return [substance for *_, substance in scored[:limit]]
