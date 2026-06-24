#!/usr/bin/env python
"""Auto-update the bundled Turkish drug snapshots from official sources.

Updates two datasets in one run:
  * TİTCK SKRS E-Reçete list  -> src/health_mcp/data/titck_drugs.json
  * SGK EK-4/A (Bedeli Ödenecek İlaçlar Listesi, from the consolidated SUT zip)
                              -> src/health_mcp/data/sgk_ek4a.json

Usage:
    python scripts/update_data.py

Schedule weekly on Windows (adjust paths):
    schtasks /Create /SC WEEKLY /D MON /ST 03:00 /TN "health-mcp-update" /TR ^
      "\"C:\\path\\.venv\\Scripts\\python.exe\" \"C:\\path\\scripts\\update_data.py\""
"""
from __future__ import annotations

import datetime as dt
import html
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

SCRIPTS = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "Mozilla/5.0 (health-mcp updater)"}

SKRS_PAGE = "https://www.titck.gov.tr/dinamikmodul/43"
SKRS_XLSX_RE = re.compile(
    r"https://titck\.gov\.tr/storage/[^\"'\s]*skrserecet[^\"'\s]*\.xlsx", re.IGNORECASE
)

SGK_BASE = "https://www.sgk.gov.tr"
SGK_GSS_INDEX = (
    SGK_BASE + "/duyuru/index/"
    "GENEL-SAGLIK-SIGORTASI-GENEL-MUDURLUGU-2026-01-28-02-00-42"
)
SGK_DETAIL_RE = re.compile(
    r"/duyuru/detay/[^\"'\s]*Islenmis-Guncel[^\"'\s]*", re.IGNORECASE
)
SGK_ZIP_RE = re.compile(r"/Download/DownloadFile\?f=[^\"'\s]+?\.zip[^\"'\s]*")


def _download(url: str, suffix: str) -> str:
    with httpx.stream(
        "GET", url, headers=HEADERS, timeout=300, follow_redirects=True
    ) as resp:
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
            return tmp.name


def _build(script: str, excel_path: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / script),
            excel_path,
            "--version",
            dt.date.today().isoformat(),
        ],
        check=True,
    )


def update_titck() -> None:
    page = httpx.get(SKRS_PAGE, headers=HEADERS, timeout=60, follow_redirects=True)
    page.raise_for_status()
    matches = SKRS_XLSX_RE.findall(page.text)
    if not matches:
        print("! TİTCK SKRS .xlsx bağlantısı bulunamadı, atlanıyor.")
        return
    print("TİTCK SKRS:", matches[0])
    xlsx = _download(matches[0], ".xlsx")
    try:
        _build("build_titck_snapshot.py", xlsx)
    finally:
        Path(xlsx).unlink(missing_ok=True)


def update_sgk() -> None:
    idx = httpx.get(SGK_GSS_INDEX, headers=HEADERS, timeout=60, follow_redirects=True)
    idx.raise_for_status()
    detail_match = SGK_DETAIL_RE.search(idx.text)
    if not detail_match:
        print("! SGK 'İşlenmiş Güncel SUT' duyurusu bulunamadı, atlanıyor.")
        return
    detail = httpx.get(
        SGK_BASE + detail_match.group(0),
        headers=HEADERS,
        timeout=60,
        follow_redirects=True,
    )
    detail.raise_for_status()
    zip_match = SGK_ZIP_RE.search(detail.text)
    if not zip_match:
        print("! SGK SUT zip bağlantısı bulunamadı, atlanıyor.")
        return
    zip_url = SGK_BASE + html.unescape(zip_match.group(0))
    print("SGK SUT zip:", zip_url)
    zip_path = _download(zip_url, ".zip")
    try:
        with zipfile.ZipFile(zip_path) as archive:
            targets = [
                n
                for n in archive.namelist()
                if "EK-4A BEDEL" in n and "LGA" not in n
            ]
            if not targets:
                print("! EK-4A zip içinde bulunamadı, atlanıyor.")
                return
            xlsx_path = zip_path + "_ek4a.xlsx"
            with archive.open(targets[0]) as src, open(xlsx_path, "wb") as dst:
                dst.write(src.read())
        try:
            _build("build_sgk_snapshot.py", xlsx_path)
        finally:
            Path(xlsx_path).unlink(missing_ok=True)
    finally:
        Path(zip_path).unlink(missing_ok=True)


def main() -> None:
    print("== TİTCK SKRS güncelleniyor ==")
    update_titck()
    print("\n== SGK EK-4/A güncelleniyor ==")
    update_sgk()
    print("\n✓ Tüm güncellemeler tamamlandı.")


if __name__ == "__main__":
    main()
