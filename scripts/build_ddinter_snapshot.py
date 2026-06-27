#!/usr/bin/env python
"""Build a compact DDInter drug-drug interaction snapshot.

Downloads the eight ATC-category CSVs published by DDInter 2.0 and writes a
compact lookup table to ``src/health_mcp/data/ddinter_interactions.json``.

DDInter data is licensed **CC BY-NC-SA 4.0** (https://ddinter.scbdd.com/terms/):
non-commercial use only, attribution required, ShareAlike. The completeness
disclaimer matters clinically — the ABSENCE of a pair does NOT prove the
combination is safe.

Usage:
    python scripts/build_ddinter_snapshot.py [--version YYYY-MM-DD]
    python scripts/build_ddinter_snapshot.py --source-dir path/with/csvs
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
from pathlib import Path

import httpx

BASE = "https://ddinter.scbdd.com/static/media/download/"
CODES = ["A", "B", "D", "H", "L", "P", "R", "V"]
OUT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "health_mcp"
    / "data"
    / "ddinter_interactions.json"
)
# Severity rank — higher wins when the same pair appears in several files.
LEVELS = {"Minor": 1, "Moderate": 2, "Major": 3, "Unknown": 0}
HEADERS = {"User-Agent": "Mozilla/5.0 (klinik-mcp build)"}


def _fetch(code: str) -> str:
    url = f"{BASE}ddinter_downloads_code_{code}.csv"
    resp = httpx.get(url, timeout=180.0, headers=HEADERS, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=dt.date.today().isoformat())
    parser.add_argument(
        "--source-dir",
        help="Optional directory with pre-downloaded ddinter_downloads_code_*.csv",
    )
    args = parser.parse_args()

    drug_index: dict[str, int] = {}
    drugs: list[str] = []
    pairs: dict[tuple[int, int], int] = {}

    def idx(name: str) -> int:
        if name not in drug_index:
            drug_index[name] = len(drugs)
            drugs.append(name)
        return drug_index[name]

    for code in CODES:
        if args.source_dir:
            path = Path(args.source_dir) / f"ddinter_downloads_code_{code}.csv"
            text = path.read_text(encoding="utf-8")
        else:
            print(f"indiriliyor: code_{code} …")
            text = _fetch(code)
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            a = (row.get("Drug_A") or "").strip()
            b = (row.get("Drug_B") or "").strip()
            level = (row.get("Level") or "").strip()
            if not a or not b or a.casefold() == b.casefold():
                continue
            ia, ib = idx(a), idx(b)
            lo, hi = (ia, ib) if ia < ib else (ib, ia)
            rank = LEVELS.get(level, 0)
            prev = pairs.get((lo, hi))
            if prev is None or rank > prev:
                pairs[(lo, hi)] = rank

    pair_list = [[a, b, lv] for (a, b), lv in pairs.items()]
    payload = {
        "meta": {
            "source": "DDInter 2.0",
            "url": "https://ddinter.scbdd.com/",
            "license": "CC BY-NC-SA 4.0",
            "license_url": "https://ddinter.scbdd.com/terms/",
            "version": args.version,
            "drug_count": len(drugs),
            "pair_count": len(pair_list),
            "levels": {"0": "Unknown", "1": "Minor", "2": "Moderate", "3": "Major"},
            "disclaimer": (
                "Bir kombinasyonun bu listede olmaması, etkileşim olmadığını "
                "KANITLAMAZ."
            ),
        },
        "drugs": drugs,
        "pairs": pair_list,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    print(f"YAZILDI {OUT}  ilaç={len(drugs)}  çift={len(pair_list)}")


if __name__ == "__main__":
    main()
