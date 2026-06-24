"""Optional barcode -> TL price lookup, fed from a commercial/pharmacy export.

``data/prices.json`` schema::

    {"meta": {"source": "...", "version": "...", "currency": "TRY", "sample": false},
     "prices": {"<barcode>": {"depot": 12.34, "retail": 18.50}, ...}}

If the file is absent or empty, lookups return ``None`` and the tools degrade
gracefully (they simply omit price information). Build/refresh it with
``scripts/build_prices.py`` from any barcode->price CSV/Excel.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "prices.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DATA_PATH.exists():
        return {"meta": {}, "prices": {}}
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def available() -> bool:
    return bool(_load().get("prices"))


def meta() -> dict:
    return _load().get("meta", {})


def lookup(barcode: str | None) -> dict | None:
    if not barcode:
        return None
    return _load().get("prices", {}).get(str(barcode).strip())


def retail(barcode: str | None) -> float | None:
    entry = lookup(barcode)
    value = entry.get("retail") if entry else None
    return value if isinstance(value, (int, float)) else None
