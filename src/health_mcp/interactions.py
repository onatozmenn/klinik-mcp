"""Pairwise drug-drug interaction lookup over a bundled DDInter 2.0 snapshot.

Data source: DDInter 2.0 (https://ddinter.scbdd.com/), licensed **CC BY-NC-SA
4.0** (non-commercial; attribution required). The *absence* of a pair does NOT
prove the combination is safe.

Drug resolution is **exact** (normalized) only — never fuzzy — so each query
maps to a single DDInter substance or is reported as unresolved. Turkish
brand/active names are bridged through the TİTCK SKRS ATC substance name
(``atc_name``), which is already an English INN for single-substance products.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from . import titck

DATA_PATH = Path(__file__).parent / "data" / "ddinter_interactions.json"

_LEVELS = {0: "Unknown", 1: "Minor", 2: "Moderate", 3: "Major"}

# Hand-verified synonyms → exact DDInter canonical name. DDInter makes specific
# INN choices (Salbutamol not Albuterol, Glyburide not Glibenclamide, Lithium
# carbonate not Lithium, Rifampicin not Rifampin, Cephalexin not Cefalexin);
# every target below was verified to exist in the snapshot.
_ALIAS_RAW: dict[str, str] = {
    # English alternates / US names → DDInter INN
    "aspirin": "Acetylsalicylic acid",
    "asa": "Acetylsalicylic acid",
    "paracetamol": "Acetaminophen",
    "albuterol": "Salbutamol",
    "adrenaline": "Epinephrine",
    "noradrenaline": "Norepinephrine",
    "frusemide": "Furosemide",
    "rifampin": "Rifampicin",
    "glibenclamide": "Glyburide",
    "pethidine": "Meperidine",
    "lignocaine": "Lidocaine",
    "amoxycillin": "Amoxicillin",
    "cefalexin": "Cephalexin",
    "lithium": "Lithium carbonate",
    # Turkish INN spellings → DDInter INN
    "varfarin": "Warfarin",
    "asetilsalisilik asit": "Acetylsalicylic acid",
    "parasetamol": "Acetaminophen",
    "asetaminofen": "Acetaminophen",
    "digoksin": "Digoxin",
    "klaritromisin": "Clarithromycin",
    "amiodaron": "Amiodarone",
    "siprofloksasin": "Ciprofloxacin",
    "sefaleksin": "Cephalexin",
    "azitromisin": "Azithromycin",
    "omeprazol": "Omeprazole",
    "fluoksetin": "Fluoxetine",
    "sitalopram": "Citalopram",
    "sertralin": "Sertraline",
    "kodein": "Codeine",
    "spironolakton": "Spironolactone",
    "fenitoin": "Phenytoin",
    "karbamazepin": "Carbamazepine",
    "lityum": "Lithium carbonate",
    "metotreksat": "Methotrexate",
    "klopidogrel": "Clopidogrel",
    "glibenklamid": "Glyburide",
    "rifampisin": "Rifampicin",
    "metronidazol": "Metronidazole",
    "flukonazol": "Fluconazole",
    "ketokonazol": "Ketoconazole",
    "teofilin": "Theophylline",
    "adrenalin": "Epinephrine",
    "noradrenalin": "Norepinephrine",
    "furosemid": "Furosemide",
    "lidokain": "Lidocaine",
    "amoksisilin": "Amoxicillin",
}


def _normalize(text: str) -> str:
    text = (text or "").upper().translate(str.maketrans("ÇĞİÖŞÜ", "CGIOSU"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_PATH.exists():
        return {"meta": {}, "drugs": [], "pairs": []}
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def meta() -> dict:
    return _load().get("meta", {})


def available() -> bool:
    return bool(_load().get("pairs"))


@lru_cache(maxsize=1)
def _indices() -> tuple[
    list[str], dict[str, int], dict[tuple[int, int], int], dict[str, str]
]:
    data = _load()
    drugs: list[str] = data.get("drugs", [])
    by_name: dict[str, int] = {}
    for i, name in enumerate(drugs):
        by_name.setdefault(_normalize(name), i)
    pair_map: dict[tuple[int, int], int] = {
        (a, b): lv for a, b, lv in data.get("pairs", [])
    }
    alias = {_normalize(k): _normalize(v) for k, v in _ALIAS_RAW.items()}
    return drugs, by_name, pair_map, alias


def resolve(query: str) -> dict | None:
    """Resolve a query to a single DDInter substance, or ``None``.

    Order: synonym table → direct DDInter name → TİTCK SKRS bridge (brand/active
    name → single-substance ``atc_name``). Exact normalized match only; the
    function never guesses a fuzzy match.
    """
    drugs, by_name, _, alias = _indices()
    norm = _normalize(query)
    if not norm:
        return None
    target = alias.get(norm, norm)
    idx = by_name.get(target)
    if idx is not None:
        return {"name": drugs[idx], "index": idx, "via": "ddinter"}

    record = titck.resolve(query)
    candidates = []
    if record:
        candidates.append(record)
    # Also scan further name matches so a single-substance product (e.g. plain
    # "PAROL") is preferred over a combination that happened to match first.
    candidates.extend(titck.search_by_name(query, limit=10))
    for rec in candidates:
        atc_name = rec.get("atc_name") or ""
        atc_code = rec.get("atc_code") or ""
        # Only a 5th-level ATC code (7+ chars) denotes a single substance; skip
        # ATC class rows and explicit combination products.
        if len(atc_code) >= 7 and "combination" not in atc_name.lower():
            bridged = alias.get(_normalize(atc_name), _normalize(atc_name))
            bidx = by_name.get(bridged)
            if bidx is not None:
                return {
                    "name": drugs[bidx],
                    "index": bidx,
                    "via": "titck",
                    "titck_name": rec.get("name"),
                }
    return None


def check_pair(query_a: str, query_b: str) -> dict:
    """Resolve both queries and return their pairwise interaction severity."""
    _, _, pair_map, _ = _indices()
    ra = resolve(query_a)
    rb = resolve(query_b)
    result: dict = {"a": ra, "b": rb, "level": None, "level_label": None}
    if ra and rb:
        if ra["index"] == rb["index"]:
            result["same"] = True
            return result
        lo, hi = sorted((ra["index"], rb["index"]))
        code = pair_map.get((lo, hi))
        if code is not None:
            result["level"] = code
            result["level_label"] = _LEVELS.get(code, "Unknown")
    return result
