"""Loader and query helpers for the bundled TİTCK drug-safety snapshot.

Two official TİTCK lists, clinically relevant at the point of care:

* **Ek İzlemeye Tabi İlaçlar** (additional monitoring, ▼) — ``dinamikmodul/57``
* **Ruhsat İptal Listesi** (authorization cancellations) — ``dinamikmodul/76``

The snapshot (``data/titck_safety.json``) is produced by
``scripts/build_titck_safety_snapshot.py``. At runtime only the JSON is read; if
it is empty the safety tools degrade gracefully (they simply report no record).
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "titck_safety.json"


def _normalize(text: str) -> str:
    text = (text or "").upper().translate(str.maketrans("ÇĞİÖŞÜ", "CGIOSU"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def _first_token(text: str) -> str:
    normalized = _normalize(text)
    return normalized.split(" ")[0] if normalized else ""


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_PATH.exists():
        return {"meta": {}, "monitoring": [], "cancellations": []}
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def meta() -> dict:
    return _load().get("meta", {})


def available() -> bool:
    data = _load()
    return bool(data.get("monitoring") or data.get("cancellations"))


@lru_cache(maxsize=1)
def _indices() -> tuple[dict, dict, dict, dict]:
    data = _load()
    mon_by_name: dict[str, dict] = {}
    mon_by_active: dict[str, dict] = {}
    for entry in data.get("monitoring", []):
        token = _first_token(entry.get("name", ""))
        if token:
            mon_by_name.setdefault(token, entry)
        active = _normalize(entry.get("active", ""))
        if active:
            mon_by_active.setdefault(active, entry)

    cancel_by_name: dict[str, list[dict]] = {}
    cancel_by_barcode: dict[str, dict] = {}
    for entry in data.get("cancellations", []):
        token = _first_token(entry.get("name", ""))
        if token:
            cancel_by_name.setdefault(token, []).append(entry)
        barcode = str(entry.get("barcode", "")).strip()
        if barcode:
            cancel_by_barcode[barcode] = entry
    return mon_by_name, mon_by_active, cancel_by_name, cancel_by_barcode


def monitoring_status(name: str | None = None, active: str | None = None) -> dict | None:
    """Return the additional-monitoring record for a drug name/active, or None.

    Matches by the drug name's first token (brand or "X içeren tüm ilaçlar"
    entries) and by active ingredient.
    """
    mon_by_name, mon_by_active, _, _ = _indices()
    for candidate in (
        mon_by_name.get(_first_token(name)) if name else None,
        mon_by_active.get(_first_token(name)) if name else None,
        mon_by_active.get(_normalize(active)) if active else None,
    ):
        if candidate:
            return candidate
    return None


def cancellation_status(
    name: str | None = None, barcode: str | None = None
) -> list[dict]:
    """Return authorization-cancellation records for a name or barcode.

    A name may match several cancelled products/presentations, so a list is
    returned (empty when there is no record).
    """
    _, _, cancel_by_name, cancel_by_barcode = _indices()
    if barcode:
        entry = cancel_by_barcode.get(str(barcode).strip())
        if entry:
            return [entry]
    if name:
        return cancel_by_name.get(_first_token(name), [])
    return []
