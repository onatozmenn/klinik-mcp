"""Klinik MCP — drug & clinical information server for Turkish clinicians.

Combines Turkey-specific data (TİTCK drug registry & safety, SGK EK-4/A
reimbursement/equivalents) with universal clinical tools (openFDA labels &
interactions, RxClass/ATC, PubMed) and bedside calculators, exposed as MCP
tools/prompts/resources for Claude, ChatGPT and other MCP clients.
"""
from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import clinical, foreign, interactions, safety, sgk, titck
from .clients import kubkt, openfda, pubmed, rxnorm
from .clients.http import APIError

mcp = FastMCP(
    name="Klinik MCP",
    instructions=(
        "Klinik MCP — drug & clinical information tools for Turkish physicians "
        "and pharmacists. Capabilities: (1) openFDA drug labels, adverse events "
        "(FAERS), plus condition\u2192drug reverse lookup; (2) NLM RxClass for "
        "therapeutic/ATC/mechanism classes; (3) PubMed medical-literature "
        "search; (4) clinical calculators (Cockcroft\u2013Gault creatinine "
        "clearance, Mosteller body-surface-area, weight-based pediatric dose); "
        "(5) Turkey-specific data \u2014 T\u0130TCK SKRS drug registry (search by "
        "name, full info, drugs sharing an ATC code), official T\u0130TCK K\u00dcB/KT "
        "product leaflets (SmPC for clinicians & patient information), T\u0130TCK "
        "safety status (additional monitoring \u25bc and authorization "
        "cancellations), a T\u0130TCK foreign-supply (yurt d\u0131\u015f\u0131) active-substance "
        "list, and SGK EK-4/A bioequivalents & reimbursement status; (6) pairwise "
        "drug\u2013drug interaction severity from DDInter, with Turkish brand/active-name "
        "bridging. "
        "Replies are in Turkish. All data is educational only and is NOT medical "
        "advice; always advise consulting a qualified healthcare professional."
    ),
)

DISCLAIMER = (
    "\n\n---\n*Bu bilgi yalnızca eğitim amaçlıdır, tıbbi tavsiye değildir. "
    "Kaynaklar: openFDA, NLM RxNorm/RxClass & PubMed. Tıbbi "
    "kararlar için bir sağlık profesyoneline danışın.*"
)

CALC_DISCLAIMER = (
    "\n\n---\n*Hesaplama standart formüllere dayanır (eğitim amaçlı), tıbbi "
    "tavsiye değildir. Doz/klinik kararlar için sorumlu hekime danışın.*"
)


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def _clean(term: str) -> str:
    """Strip characters that would break the upstream query syntax."""
    return term.replace('"', " ").replace("\\", " ").strip()


def _join(value) -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value) if value else ""


def _truncate(text: str, limit: int = 1500) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …"


def _fmt_date(value: str | None) -> str:
    if value and len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value or "?"


def _label_header(openfda_info: dict, fallback: str) -> str:
    brand = _join(openfda_info.get("brand_name")) or fallback
    generic = _join(openfda_info.get("generic_name"))
    route = _join(openfda_info.get("route"))
    manufacturer = _join(openfda_info.get("manufacturer_name"))
    lines = [f"# {brand}"]
    if generic:
        lines.append(f"**Etken madde:** {generic}")
    if route:
        lines.append(f"**Veriliş yolu:** {route}")
    if manufacturer:
        lines.append(f"**Üretici:** {manufacturer}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool behaviour hints — every tool is read-only & idempotent. "API" tools reach
# external services (open world); "LOCAL" tools read bundled data / pure math.
# --------------------------------------------------------------------------- #
_API_TOOL = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)
_LOCAL_TOOL = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool(annotations=_API_TOOL)
async def get_drug_label(
    drug_name: Annotated[str, Field(description="Drug name (brand, generic, or active substance).")],
) -> str:
    """Get the official openFDA label for a drug.

    Includes indications, dosage & administration, warnings, contraindications,
    drug interactions and adverse reactions.
    """
    name = _clean(drug_name)
    if not name:
        return "Lütfen bir ilaç adı girin."
    try:
        results = await openfda.drug_label(name, limit=1)
    except APIError as exc:
        return f"openFDA isteği başarısız oldu: {exc}"
    if not results:
        return f"'{drug_name}' için openFDA ilaç etiketi bulunamadı."

    result = results[0]
    header = _label_header(result.get("openfda", {}), drug_name)
    sections = []
    for title, field in (
        ("Endikasyonlar (Indications & Usage)", "indications_and_usage"),
        ("Doz / Kullanım (Dosage & Administration)", "dosage_and_administration"),
        ("Uyarılar (Warnings)", "warnings"),
        ("Kontrendikasyonlar (Contraindications)", "contraindications"),
        ("İlaç Etkileşimleri (Drug Interactions)", "drug_interactions"),
        ("Yan Etkiler (Adverse Reactions)", "adverse_reactions"),
    ):
        text = _join(result.get(field))
        if text:
            sections.append(f"### {title}\n{_truncate(text)}")
    body = "\n\n".join(sections) if sections else "_Etiket metni bulunamadı._"
    return f"{header}\n\n{body}{DISCLAIMER}"


@mcp.tool(annotations=_API_TOOL)
async def get_drug_interactions(
    drug_name: Annotated[str, Field(description="Drug name (brand, generic, or active substance).")],
) -> str:
    """Get the drug-interactions section from a drug's openFDA label."""
    name = _clean(drug_name)
    if not name:
        return "Lütfen bir ilaç adı girin."
    try:
        results = await openfda.drug_label(name, limit=1)
    except APIError as exc:
        return f"openFDA isteği başarısız oldu: {exc}"
    if not results:
        return f"'{drug_name}' için etiket bulunamadı."

    text = _join(results[0].get("drug_interactions"))
    if not text:
        return (
            f"'{drug_name}' etiketinde listelenmiş ilaç etkileşimi bilgisi yok."
            + DISCLAIMER
        )
    return f"# {drug_name} — İlaç Etkileşimleri\n\n{_truncate(text, 3000)}{DISCLAIMER}"


@mcp.tool(annotations=_API_TOOL)
async def get_drug_adverse_events(
    drug_name: Annotated[str, Field(description="Drug name (brand, generic, or active substance).")],
    limit: Annotated[int, Field(description="Maximum number of adverse-event terms to return.")] = 10,
) -> str:
    """Get the most frequently reported adverse events for a drug (FAERS).

    Data comes from the openFDA adverse-event reporting system. Counts reflect
    spontaneous reports and do not imply causation.
    """
    name = _clean(drug_name)
    if not name:
        return "Lütfen bir ilaç adı girin."
    try:
        results = await openfda.adverse_event_counts(name, limit=limit)
    except APIError as exc:
        return f"openFDA isteği başarısız oldu: {exc}"
    if not results:
        return f"'{drug_name}' için bildirilmiş yan etki verisi bulunamadı."

    lines = [
        f"# {drug_name} — En Sık Bildirilen Yan Etkiler (FAERS)\n",
        "| Yan Etki | Bildirim Sayısı |",
        "| --- | ---: |",
    ]
    for item in results:
        term = str(item.get("term", "?")).title()
        count = item.get("count", 0)
        lines.append(f"| {term} | {count:,} |")
    return "\n".join(lines) + DISCLAIMER


@mcp.tool(annotations=_API_TOOL)
async def find_drugs_for_condition(
    condition: Annotated[str, Field(description="Condition/indication, e.g. 'hypertension' or 'migraine'.")],
    max_results: Annotated[int, Field(description="Maximum number of drugs to return.")] = 10,
) -> str:
    """Find drugs whose FDA labels list a given condition as an indication.

    Reverse lookup: given a condition (e.g. "hypertension", "migraine"), returns
    the generic drugs most frequently indicated for it.
    """
    term = _clean(condition)
    if not term:
        return "Lütfen bir hastalık/durum girin."
    try:
        results = await openfda.drugs_for_indication(term, limit=max_results)
    except APIError as exc:
        return f"openFDA isteği başarısız oldu: {exc}"
    if not results:
        return f"'{condition}' için endikasyonu olan ilaç bulunamadı."

    lines = [
        f"# '{condition}' için kullanılan ilaçlar\n",
        "| İlaç (etken madde) | Etiket sayısı |",
        "| --- | ---: |",
    ]
    for item in results:
        name = str(item.get("term", "?")).title()
        lines.append(f"| {name} | {item.get('count', 0):,} |")
    return "\n".join(lines) + DISCLAIMER


@mcp.tool(annotations=_API_TOOL)
async def get_drug_classes(
    drug_name: Annotated[str, Field(description="Drug name to look up therapeutic/ATC/mechanism classes for.")],
) -> str:
    """List the therapeutic / ATC / mechanism classes a drug belongs to (RxClass)."""
    name = _clean(drug_name)
    if not name:
        return "Lütfen bir ilaç adı girin."
    try:
        ids = await rxnorm.rxcui_by_name(name)
        if not ids:
            candidates = await rxnorm.approximate_term(name, max_entries=1)
            ids = [candidates[0]["rxcui"]] if candidates else []
        if not ids:
            return f"'{drug_name}' için RxNorm kaydı bulunamadı."
        infos = await rxnorm.classes_by_rxcui(ids[0])
    except APIError as exc:
        return f"RxClass isteği başarısız oldu: {exc}"
    if not infos:
        return f"'{drug_name}' için sınıf bilgisi bulunamadı." + DISCLAIMER

    grouped: dict[str, list[str]] = {}
    for info in infos:
        concept = info.get("rxclassMinConceptItem", {})
        class_type = concept.get("classType", "Diğer")
        class_name = concept.get("className")
        if class_name and class_name not in grouped.setdefault(class_type, []):
            grouped[class_type].append(class_name)

    labels = {
        "ATC1-4": "ATC sınıfı",
        "MOA": "Etki mekanizması (MoA)",
        "PE": "Fizyolojik etki",
        "EPC": "Farmakolojik sınıf (EPC)",
        "DISEASE": "İlişkili hastalık",
        "CHEM": "Kimyasal yapı",
        "TC": "Terapötik sınıf",
    }
    lines = [f"# {drug_name} — İlaç Sınıfları (RxClass)\n"]
    for class_type, names in grouped.items():
        title = labels.get(class_type, class_type)
        lines.append(f"**{title}:** {', '.join(sorted(names)[:10])}")
    return "\n".join(lines) + DISCLAIMER


@mcp.tool(annotations=_API_TOOL)
async def search_medical_literature(
    query: Annotated[str, Field(description="Topic to search — drug, condition, or keyword.")],
    max_results: Annotated[int, Field(description="Maximum number of articles to return.")] = 10,
) -> str:
    """Search PubMed for medical literature on a drug, condition or topic."""
    term = _clean(query)
    if not term:
        return "Lütfen bir konu (ilaç, hastalık vb.) girin."
    try:
        pmids = await pubmed.search(term, retmax=max_results)
        results = await pubmed.summaries(pmids)
    except APIError as exc:
        return f"PubMed isteği başarısız oldu: {exc}"
    if not pmids:
        return f"'{query}' için PubMed makalesi bulunamadı."

    blocks = [f"# '{query}' — PubMed Makaleleri\n"]
    for pmid in pmids:
        item = results.get(pmid)
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "(başlıksız)")).rstrip(".")
        journal = item.get("fulljournalname") or item.get("source", "")
        pubdate = item.get("pubdate", "")
        authors = item.get("authors", [])
        first_author = ""
        if authors and isinstance(authors[0], dict):
            first_author = authors[0].get("name", "")
        meta = " · ".join(x for x in [first_author, journal, pubdate] if x)
        blocks.append(
            f"### {title}\n"
            f"{meta}\n"
            f"[PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
        )
    return "\n\n".join(blocks) + DISCLAIMER


@mcp.tool(annotations=_API_TOOL)
async def get_drug_leaflet(
    query: Annotated[str, Field(description="Turkish drug name to find its official KÜB/KT leaflet for.")],
    max_results: Annotated[int, Field(description="Maximum number of matching products to return.")] = 5,
) -> str:
    """Resmi TİTCK KÜB (Kısa Ürün Bilgisi — hekim) ve KT (Kullanma Talimatı — hasta) prospektüs bağlantıları.

    Looks up a Turkish drug in TİTCK's official KÜB/KT registry and returns the
    official SmPC (KÜB, for clinicians) and patient-leaflet (KT) PDF links.
    """
    term = _clean(query)
    if not term:
        return "Lütfen bir ilaç adı girin."
    try:
        rows = await kubkt.search_leaflets(term, limit=max_results)
    except APIError as exc:
        return f"KÜB/KT isteği başarısız oldu: {exc}"
    if not rows:
        return f"'{query}' için TİTCK KÜB/KT kaydı bulunamadı."
    blocks = [f"# '{query}' — Resmi Prospektüs (KÜB/KT)\n"]
    for row in rows:
        parts = [f"### {row['name']}"]
        if row.get("active"):
            parts.append(f"**Etken madde:** {row['active']}")
        if row.get("company"):
            parts.append(f"**Firma:** {row['company']}")
        links = []
        if row.get("kub_url"):
            links.append(f"[KÜB — hekim]({row['kub_url']})")
        if row.get("kt_url"):
            links.append(f"[KT — hasta]({row['kt_url']})")
        parts.append(" · ".join(links) if links else "_Doküman bağlantısı yok._")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks) + DISCLAIMER


@mcp.tool(annotations=_LOCAL_TOOL)
def creatinine_clearance(
    age: Annotated[float, Field(description="Patient age in years.")],
    weight_kg: Annotated[float, Field(description="Body weight in kilograms.")],
    serum_creatinine_mg_dl: Annotated[float, Field(description="Serum creatinine in mg/dL.")],
    sex: Annotated[str, Field(description="Sex: 'kadın'/'female'/'f' or 'erkek'/'male'/'m'.")],
) -> str:
    """Estimate creatinine clearance (Cockcroft–Gault) for renal drug dosing.

    sex: "kadın"/"female"/"f" or "erkek"/"male"/"m".
    serum_creatinine_mg_dl: serum creatinine in mg/dL.
    """
    initial = str(sex).strip().lower()[:1]
    if initial not in {"k", "f", "w", "e", "m"}:
        return (
            "Geçersiz girdi: cinsiyet 'kadın'/'erkek' (veya female/male) olarak "
            "belirtilmeli."
        )
    is_female = initial in {"k", "f", "w"}
    try:
        crcl = clinical.cockcroft_gault(age, weight_kg, serum_creatinine_mg_dl, is_female)
    except ValueError as exc:
        return f"Geçersiz girdi: {exc}"
    return (
        "# Kreatinin Klerensi (Cockcroft–Gault)\n"
        f"- **CrCl:** {crcl:.0f} mL/dk\n"
        f"- **Böbrek fonksiyonu:** {clinical.renal_function_category(crcl)}\n"
        f"- **Girdi:** {age:.0f} yaş, {weight_kg:.0f} kg, kreatinin "
        f"{serum_creatinine_mg_dl} mg/dL, {'kadın' if is_female else 'erkek'}"
        f"{CALC_DISCLAIMER}"
    )


@mcp.tool(annotations=_LOCAL_TOOL)
def body_surface_area(
    height_cm: Annotated[float, Field(description="Height in centimeters.")],
    weight_kg: Annotated[float, Field(description="Body weight in kilograms.")],
) -> str:
    """Body surface area (Mosteller formula) for BSA-based dosing."""
    try:
        bsa = clinical.mosteller_bsa(height_cm, weight_kg)
    except ValueError as exc:
        return f"Geçersiz girdi: {exc}"
    return (
        "# Vücut Yüzey Alanı (Mosteller)\n"
        f"- **BSA:** {bsa:.2f} m²\n"
        f"- **Girdi:** boy {height_cm:.0f} cm, kilo {weight_kg:.0f} kg"
        f"{CALC_DISCLAIMER}"
    )


@mcp.tool(annotations=_LOCAL_TOOL)
def pediatric_dose(
    weight_kg: Annotated[float, Field(description="Child body weight in kilograms.")],
    mg_per_kg_per_day: Annotated[float, Field(description="Dose rate in mg per kg per day, from a trusted reference.")],
    doses_per_day: Annotated[int, Field(description="Number of divided doses per day.")] = 1,
    max_mg_per_day: Annotated[float | None, Field(description="Optional maximum total daily dose (mg) to cap at.")] = None,
) -> str:
    """Weight-based pediatric dose calculator.

    Computes total daily and per-dose amounts from a mg/kg/day rate that YOU
    supply from a trusted reference; this tool only does the arithmetic
    (optionally capping at a maximum daily dose). It does not recommend doses.
    """
    if min(weight_kg, mg_per_kg_per_day) <= 0 or doses_per_day < 1:
        return "Geçersiz girdi: kilo ve doz pozitif, doz sayısı ≥1 olmalı."
    daily = weight_kg * mg_per_kg_per_day
    capped = max_mg_per_day is not None and daily > max_mg_per_day
    if capped:
        daily = max_mg_per_day
    per_dose = daily / doses_per_day
    lines = [
        "# Pediatrik Doz Hesabı (kilo bazlı)",
        f"- **Günlük toplam:** {daily:.1f} mg/gün"
        + (f" (maksimum {max_mg_per_day:.0f} mg ile sınırlandı)" if capped else ""),
        f"- **Doz başına:** {per_dose:.1f} mg × günde {doses_per_day} kez",
        f"- **Girdi:** {weight_kg:.1f} kg × {mg_per_kg_per_day:g} mg/kg/gün",
    ]
    return "\n".join(lines) + CALC_DISCLAIMER


# --------------------------------------------------------------------------- #
# Turkey-specific tools (SGK EK-4/A bundled snapshot)
# --------------------------------------------------------------------------- #
def _sgk_disclaimer() -> str:
    info = sgk.meta()
    note = ""
    if info.get("sample"):
        note = (
            "\n\n> ⚠️ **ÖRNEK VERİ** — gerçek SGK EK-4/A dosyasını yükleyin "
            "(bkz. README / scripts/build_sgk_snapshot.py)."
        )
    return (
        note
        + f"\n\n---\n*Kaynak: {info.get('source', 'SGK EK-4/A')} "
        f"({info.get('version', '?')}, {info.get('count', '?')} kayıt). Resmî "
        "güncel listeden teyit edin; eczacılık/tıbbi kararlar için yetkiliye "
        "danışın.*"
    )


def _sgk_fields(record: dict) -> list[str]:
    lines = []
    if record.get("kamu_no"):
        lines.append(f"- **Kamu No:** {record['kamu_no']}")
    if record.get("barcode"):
        lines.append(f"- **Barkod:** {record['barcode']}")
    if record.get("equivalent_group"):
        lines.append(f"- **Eşdeğer grup:** {record['equivalent_group']}")
    if record.get("entry_date"):
        lines.append(f"- **Listeye giriş:** {record['entry_date']}")
    return lines


def _resolve_sgk(query: str) -> dict | None:
    """Resolve a query to an SGK record, bridging via TİTCK barcode when the
    name format differs (e.g. SGK "FTB" vs TİTCK "FILM TABLET")."""
    record = sgk.resolve(query)
    if record:
        return record
    drug = titck.resolve(query)
    if drug and drug.get("barcode"):
        return sgk.find_by_barcode(drug["barcode"])
    return None


@mcp.tool(annotations=_LOCAL_TOOL)
def find_drug_equivalents(
    drug: Annotated[str, Field(description="Drug name or barcode.")],
    max_results: Annotated[int, Field(description="Maximum number of equivalent drugs to list.")] = 25,
) -> str:
    """Find SGK eşdeğer (bioequivalent) drugs for a drug name or barcode."""
    record = _resolve_sgk(drug)
    if not record:
        return f"'{drug}' SGK EK-4/A listesinde bulunamadı."
    group = record.get("equivalent_group")
    if not group:
        return (
            f"**{record.get('name')}** için tanımlı eşdeğer grubu yok."
            + _sgk_disclaimer()
        )
    members = sgk.group_members(group)[:max_results]
    lines = [
        f"# {record.get('name')} — Eşdeğer İlaçlar",
        f"**Eşdeğer grup:** `{group}` · **{len(members)}** ürün\n",
        "| İlaç | Barkod |",
        "| --- | --- |",
    ]
    for member in members:
        lines.append(
            f"| {member.get('name', '?')} | {member.get('barcode', '?')} |"
        )
    return "\n".join(lines) + _sgk_disclaimer()


@mcp.tool(annotations=_LOCAL_TOOL)
def get_reimbursement_status(
    drug: Annotated[str, Field(description="Drug name or barcode.")],
) -> str:
    """Check whether a drug is on the SGK reimbursement list (EK-4/A)."""
    record = _resolve_sgk(drug)
    if not record:
        return (
            f"'{drug}' SGK EK-4/A listesinde bulunamadı → geri ödeme kapsamında "
            f"değil (veya ad/barkod hatalı)." + _sgk_disclaimer()
        )
    lines = [
        f"# {record.get('name')} — Geri Ödeme Durumu",
        "- **Durum:** ✅ SGK EK-4/A listesinde (geri ödeme kapsamında)",
        *_sgk_fields(record),
    ]
    return "\n".join(lines) + _sgk_disclaimer()


# --------------------------------------------------------------------------- #
# Turkey-specific tools — TİTCK SKRS full drug registry (~7.9k active products)
# --------------------------------------------------------------------------- #
def _titck_disclaimer() -> str:
    info = titck.meta()
    return (
        f"\n\n---\n*Kaynak: {info.get('source', 'TİTCK SKRS')} "
        f"({info.get('version', '?')}, {info.get('count', '?')} aktif ürün). "
        "Resmî güncel listeden teyit edin; tıbbi/eczacılık kararları için "
        "yetkiliye danışın.*"
    )


def _titck_fields(drug: dict) -> list[str]:
    lines = []
    if drug.get("barcode"):
        lines.append(f"- **Barkod:** {drug['barcode']}")
    if drug.get("atc_code"):
        lines.append(f"- **ATC:** {drug['atc_code']} — {drug.get('atc_name', '')}")
    if drug.get("company"):
        lines.append(f"- **Firma:** {drug['company']}")
    if drug.get("prescription_type"):
        lines.append(f"- **Reçete türü:** {drug['prescription_type']}")
    if drug.get("essential"):
        lines.append("- **Temel İlaç Listesi:** ✅")
    return lines


@mcp.tool(annotations=_LOCAL_TOOL)
def search_turkish_drugs(
    query: Annotated[str, Field(description="Drug name to search in the TİTCK registry.")],
    max_results: Annotated[int, Field(description="Maximum number of results to return.")] = 15,
) -> str:
    """Search Turkey's licensed drug registry (TİTCK SKRS) by drug name."""
    matches = titck.search_by_name(query, limit=max_results)
    if not matches:
        return f"'{query}' için TİTCK listesinde ilaç bulunamadı."
    lines = [
        f"# '{query}' — TİTCK İlaç Sonuçları ({len(matches)})\n",
        "| İlaç | ATC | Firma | Reçete |",
        "| --- | --- | --- | --- |",
    ]
    for drug in matches:
        lines.append(
            f"| {drug.get('name', '?')} | {drug.get('atc_code', '')} "
            f"| {drug.get('company', '')} | {drug.get('prescription_type', '')} |"
        )
    return "\n".join(lines) + _titck_disclaimer()


@mcp.tool(annotations=_LOCAL_TOOL)
def get_turkish_drug_info(
    query: Annotated[str, Field(description="Drug name or barcode.")],
) -> str:
    """Get full TİTCK registry info for a Turkish drug by name or barcode."""
    drug = titck.resolve(query)
    if not drug:
        return f"'{query}' TİTCK listesinde bulunamadı."
    lines = [f"# {drug.get('name')}", *_titck_fields(drug)]
    lines.extend(_safety_lines(drug))
    return "\n".join(lines) + _titck_disclaimer()


@mcp.tool(annotations=_LOCAL_TOOL)
def find_drugs_by_active_ingredient(
    query: Annotated[str, Field(description="Drug name or barcode; its ATC code is used to find matches.")],
    max_results: Annotated[int, Field(description="Maximum number of drugs to list.")] = 30,
) -> str:
    """Find Turkish drugs sharing the same ATC code (same active substance/class)."""
    drug = titck.resolve(query)
    if not drug:
        return f"'{query}' TİTCK listesinde bulunamadı."
    atc = drug.get("atc_code")
    if not atc:
        return f"**{drug.get('name')}** için ATC kodu yok." + _titck_disclaimer()
    members = titck.find_by_atc(atc)[:max_results]
    lines = [
        f"# {drug.get('name')} — Aynı ATC ({atc})",
        f"**{drug.get('atc_name', '')}** · {len(members)} ürün\n",
        "| İlaç | Firma | Reçete |",
        "| --- | --- | --- |",
    ]
    for member in members:
        lines.append(
            f"| {member.get('name', '?')} | {member.get('company', '')} "
            f"| {member.get('prescription_type', '')} |"
        )
    return "\n".join(lines) + _titck_disclaimer()


# --------------------------------------------------------------------------- #
# Turkey-specific tools — TİTCK 'Yurt Dışı Etkin Madde' (foreign-supply) list.
# --------------------------------------------------------------------------- #
def _foreign_disclaimer() -> str:
    info = foreign.meta()
    return (
        f"\n\n---\n*Kaynak: {info.get('source', 'TİTCK Yurt Dışı Etkin Madde')} "
        f"({info.get('version', '?')}, {info.get('count', '?')} kayıt). Resmî güncel "
        "listeden ve TEB'den teyit edin.*"
    )


@mcp.tool(annotations=_LOCAL_TOOL)
def find_foreign_supply(
    query: Annotated[str, Field(description="Active substance, drug name, or ATC code to check against TİTCK's foreign-supply list.")],
    max_results: Annotated[int, Field(description="Maximum number of substances to return.")] = 15,
) -> str:
    """TİTCK Yurt Dışı Etkin Madde Listesi: bir etkin maddenin yurt dışından temin edilebilirliği.

    Checks whether an active substance can be supplied from abroad (via TEB),
    with ATC, pharmaceutical form, prescription type and whether import needs
    TİTCK's written approval.
    """
    matches = foreign.search_by_name(query, limit=max_results)
    drug = titck.resolve(query)
    if drug and drug.get("atc_code"):
        seen = {m.get("code") for m in matches}
        for entry in foreign.find_by_atc(drug["atc_code"]):
            if entry.get("code") not in seen:
                matches.append(entry)
                seen.add(entry.get("code"))
    matches = matches[:max_results]
    if not matches:
        return (
            f"'{query}' TİTCK Yurt Dışı Etkin Madde Listesi'nde bulunamadı."
            + _foreign_disclaimer()
        )
    lines = [
        f"# '{query}' — Yurt Dışı Etkin Madde",
        f"**{len(matches)}** kayıt\n",
        "| Etkin madde | ATC | Form | Reçete | İthal |",
        "| --- | --- | --- | --- | --- |",
    ]
    for substance in matches:
        ithal = (
            "yazılı onaysız ✓"
            if substance.get("import_without_approval")
            else "yazılı onay gerekli"
        )
        lines.append(
            f"| {substance.get('active', '?')} | {substance.get('atc_code', '')} "
            f"| {substance.get('form', '')} | {substance.get('prescription_type', '')} "
            f"| {ithal} |"
        )
    return "\n".join(lines) + _foreign_disclaimer()


# --------------------------------------------------------------------------- #
# Turkey-specific tools — TİTCK drug-safety status (additional monitoring +
# authorization cancellations; see safety.py / build_titck_safety_snapshot.py)
# --------------------------------------------------------------------------- #
def _safety_disclaimer() -> str:
    info = safety.meta()
    parts = []
    mon = info.get("monitoring", {})
    can = info.get("cancellations", {})
    if mon.get("count"):
        parts.append(f"ek izleme {mon.get('version', '?')} ({mon.get('count')})")
    if can.get("count"):
        parts.append(f"ruhsat iptali {can.get('version', '?')} ({can.get('count')})")
    source = "; ".join(parts) if parts else "TİTCK"
    return (
        f"\n\n---\n*Kaynak: TİTCK ({source}). Eşleşme ilaç adı/etkin madde "
        "bazlıdır; ürün/sunum farkları için resmî güncel listeden teyit edin.*"
    )


def _safety_lines(drug: dict) -> list[str]:
    """Compact safety flags for a resolved TİTCK drug (used inline in info)."""
    lines: list[str] = []
    if safety.monitoring_status(name=drug.get("name")):
        lines.append(
            "- **▼ Ek izleme:** Ek izlemeye tabi ilaç (advers etkileri TÜFAM'a bildirin)"
        )
    cancellations = safety.cancellation_status(
        name=drug.get("name"), barcode=drug.get("barcode")
    )
    if cancellations:
        lines.append(
            f"- **⛔ Ruhsat iptali:** Bu ada ait {len(cancellations)} iptal kaydı "
            "var (ürün/sunum bazında) — teyit edin"
        )
    return lines


@mcp.tool(annotations=_LOCAL_TOOL)
def get_drug_safety_status(
    query: Annotated[str, Field(description="Drug name or barcode.")],
) -> str:
    """TİTCK güvenlik durumu: ek izleme (▼) ve ruhsat iptali. Ad veya barkod.

    Reports whether a Turkish drug is on TİTCK's additional-monitoring list and
    whether any authorization-cancellation record matches its name/barcode.
    """
    if not safety.available():
        return (
            "TİTCK güvenlik verisi yüklü değil. `scripts/build_titck_safety_"
            "snapshot.py` ile ek izleme + ruhsat iptal listelerini yükleyin "
            "(bkz. README)."
        )
    drug = titck.resolve(query)
    name = drug.get("name") if drug else query
    barcode = (
        drug.get("barcode")
        if drug
        else (query.strip() if query.strip().isdigit() else None)
    )
    monitoring = safety.monitoring_status(name=name)
    cancellations = safety.cancellation_status(name=name, barcode=barcode)
    lines = [f"# {name} — TİTCK Güvenlik Durumu"]
    if monitoring:
        lines.append(
            f"- **▼ Ek izlemeye tabi** (etkin madde: {monitoring.get('active', '?')}"
            f", liste tarihi: {monitoring.get('date', '?')})"
        )
        lines.append(
            "  Yakından izlenen ilaç; şüpheli advers etkileri TÜFAM'a bildirin."
        )
    else:
        lines.append("- ▼ Ek izleme: kayıt bulunamadı")
    if cancellations:
        lines.append(
            f"- **⛔ Ruhsat iptal kaydı: {len(cancellations)}** (ürün/sunum bazında)"
        )
        for record in cancellations[:10]:
            when = record.get("cancel_date") or record.get("sheet", "")
            holder = record.get("holder", "")
            lines.append(f"  - {record.get('name', '?')} — {holder} ({when})")
    else:
        lines.append("- ⛔ Ruhsat iptali: kayıt bulunamadı")
    return "\n".join(lines) + _safety_disclaimer()


# --------------------------------------------------------------------------- #
# Universal tool — pairwise drug-drug interaction severity (DDInter 2.0; see
# interactions.py / build_ddinter_snapshot.py). Turkish names bridged via TİTCK.
# --------------------------------------------------------------------------- #
def _ddi_disclaimer() -> str:
    version = interactions.meta().get("version", "")
    suffix = f" · sürüm {version}" if version else ""
    return (
        f"\n\n---\n*Kaynak: DDInter 2.0 (CC BY-NC-SA 4.0), ddinter.scbdd.com{suffix}. "
        "Bir etkileşimin listede olmaması güvenli olduğunu göstermez. Yalnızca "
        "eğitim amaçlıdır, tıbbi tavsiye değildir; klinik kararlar için sorumlu "
        "hekim/eczacıya danışın.*"
    )


_DDI_BADGE = {
    "Major": "🔴 Major (Yüksek)",
    "Moderate": "🟠 Moderate (Orta)",
    "Minor": "🟡 Minor (Düşük)",
    "Unknown": "⚪ Bilinmiyor",
}
_DDI_NOTE = {
    "Major": "Yaşamı tehdit edebilir ve/veya ciddi yan etkiyi önlemek için tıbbi müdahale gerektirir.",
    "Moderate": "Hastanın durumunu kötüleştirebilir ve/veya tedavi değişikliği gerektirebilir.",
    "Minor": "Klinik etki sınırlıdır; genellikle tedavi değişikliği gerektirmez.",
    "Unknown": "Şiddet sınıflandırması mevcut değil.",
}


@mcp.tool(annotations=_LOCAL_TOOL)
def check_drug_interactions(
    drug1: Annotated[str, Field(description="First drug — brand, active substance, or INN (Turkish or English).")],
    drug2: Annotated[str, Field(description="Second drug — brand, active substance, or INN (Turkish or English).")],
) -> str:
    """İki ilaç arasındaki etkileşim şiddetini kontrol eder (DDInter 2.0).

    Resolves each drug to a DDInter substance (synonym table, direct name, or a
    TİTCK brand/active-name → ATC-substance bridge) and returns the pairwise
    severity (Major / Moderate / Minor). A missing pair is reported as "no
    recorded interaction", which does NOT prove the combination is safe.
    """
    if not _clean(drug1) or not _clean(drug2):
        return "Lütfen iki ilaç adı girin."
    if not interactions.available():
        return (
            "DDInter etkileşim verisi yüklü değil. `scripts/build_ddinter_"
            "snapshot.py` ile yükleyin (bkz. README)."
        )
    res = interactions.check_pair(drug1, drug2)
    a, b = res["a"], res["b"]
    unresolved = [q for q, r in ((drug1, a), (drug2, b)) if not r]
    if unresolved:
        names = ", ".join(f"'{u}'" for u in unresolved)
        return (
            f"Şu ilaç(lar) DDInter listesinde bulunamadı: {names}. Etkin maddeyi "
            "veya uluslararası adı (INN) deneyin (ör. Aspirin → Acetylsalicylic "
            "acid)." + _ddi_disclaimer()
        )
    name_a, name_b = a["name"], b["name"]
    if res.get("same"):
        return (
            f"'{drug1}' ve '{drug2}' aynı etkin maddeye (**{name_a}**) "
            "çözümlendi; etkileşim sorgusu için iki farklı ilaç girin."
            + _ddi_disclaimer()
        )
    header = f"# İlaç Etkileşimi: {name_a} × {name_b}"
    label = res["level_label"]
    if label is None:
        body = (
            "✅ DDInter veritabanında bu ikisi arasında **kayıtlı etkileşim "
            "bulunamadı.**\n\n"
            "> ⚠️ Bu, kombinasyonun güvenli olduğunu **kanıtlamaz** — DDInter "
            "her etkileşimi içermeyebilir."
        )
        lines = [header, "", body]
    else:
        lines = [header, "", f"**Şiddet: {_DDI_BADGE[label]}**", "", _DDI_NOTE[label]]
    bridged = [r for r in (a, b) if r.get("via") == "titck"]
    if bridged:
        notes = "; ".join(f"{r['titck_name']} → {r['name']}" for r in bridged)
        lines += ["", f"*Çözümleme: {notes} (TİTCK ATC köprüsü)*"]
    return "\n".join(lines) + _ddi_disclaimer()


# --------------------------------------------------------------------------- #
# Discovery: static MCP server card. Registries (e.g. Smithery) read this when
# live scanning is blocked. Served at /.well-known/mcp/server-card.json on the
# HTTP transport.
# --------------------------------------------------------------------------- #
SERVER_CARD = {
    "serverInfo": {"name": "Klinik MCP", "version": "0.1.0"},
    "authentication": {"required": False},
}


async def _server_card(request: Request) -> JSONResponse:
    """Return the static MCP server card (serverInfo + tool summary)."""
    card = dict(SERVER_CARD)
    try:
        tools = await mcp.list_tools()
        card["tools"] = sorted(
            (
                {
                    "name": tool.name,
                    "description": (getattr(tool, "description", "") or "").strip(),
                }
                for tool in tools
            ),
            key=lambda item: item["name"],
        )
    except Exception:  # registry card must stay valid even if introspection fails
        pass
    return JSONResponse(card)


mcp.custom_route("/.well-known/mcp/server-card.json", methods=["GET"])(_server_card)


async def _health(request: Request) -> JSONResponse:
    """Liveness probe for load balancers / uptime monitors."""
    try:
        tool_count = len(await mcp.list_tools())
    except Exception:
        tool_count = None
    return JSONResponse(
        {
            "status": "ok",
            "name": "Klinik MCP",
            "version": "0.1.0",
            "tool_count": tool_count,
        }
    )


mcp.custom_route("/health", methods=["GET"])(_health)


# --------------------------------------------------------------------------- #
# Prompts — one-click workflows that orchestrate several tools into a named task.
# --------------------------------------------------------------------------- #
@mcp.prompt
def ilac_bilgisi(ilac: str) -> str:
    """Bir ilaç için TİTCK kaydı, güvenlik durumu ve SGK eşdeğer/fiyatını derler."""
    return (
        f"'{ilac}' ilacı için şu araçları sırayla çağır ve sonucu tek bir özet hâlinde sun:\n"
        "1. `get_turkish_drug_info` → TİTCK kaydı (ATC, firma, reçete türü, barkod).\n"
        "2. `get_drug_safety_status` → ek izleme (▼) ve ruhsat iptali durumu.\n"
        "3. `find_drug_equivalents` → SGK eşdeğerleri ve (varsa) en ucuz muadil.\n"
        "Sonunda kısa bir klinik özet ver; bunun tıbbi tavsiye olmadığını hatırlat."
    )


@mcp.prompt
def muadil_ve_geri_odeme(ilac: str) -> str:
    """Bir ilacın SGK geri ödeme durumunu ve eşdeğer (muadil) grubunu derler."""
    return (
        f"'{ilac}' için önce `get_reimbursement_status` ile SGK geri ödeme durumunu, "
        "sonra `find_drug_equivalents` ile eşdeğer grubu ve muadilleri getir. "
        "Geri ödeme kapsamını ve muadilleri özetle; resmî güncel listeden teyit "
        "gerektiğini belirt."
    )


@mcp.prompt
def renal_doz_kontrol(
    ilac: str, yas: str, kilo: str, kreatinin: str, cinsiyet: str
) -> str:
    """Kreatinin klerensini hesaplar ve böbrek fonksiyonuna göre doz ayarını hatırlatır."""
    return (
        f"Önce `creatinine_clearance` aracını çağır (yas={yas}, kilo={kilo}, "
        f"serum_creatinine_mg_dl={kreatinin}, sex={cinsiyet}). Çıkan CrCl'ye göre "
        f"'{ilac}' için böbrek fonksiyonuna göre doz ayarlaması gerekip gerekmediğini "
        "güvenilir bir kaynaktan teyit etmesi gerektiğini açıkla. Tıbbi tavsiye "
        "olmadığını hatırlat."
    )


# --------------------------------------------------------------------------- #
# Resources — read-only reference content (in-process, no upstream calls).
# --------------------------------------------------------------------------- #
@mcp.resource("info://server")
def resource_server_info() -> str:
    """Klinik MCP hakkında genel bilgi."""
    return (
        "# Klinik MCP\n"
        "Türk hekim ve eczacılar için ilaç & klinik bilgi MCP sunucusu.\n\n"
        "- **Araçlar:** 18 (openFDA etiket/etkileşim/yan etki, DDInter ikili "
        "etkileşim, RxClass/ATC, PubMed, klinik hesaplayıcılar, TİTCK SKRS, KÜB/KT "
        "prospektüs, yurt dışı etkin madde, SGK EK-4/A, TİTCK güvenlik).\n"
        "- **Promptlar:** `ilac_bilgisi`, `muadil_ve_geri_odeme`, `renal_doz_kontrol`.\n"
        "- **Taşıma:** stdio (Claude Desktop) ve Streamable HTTP (ChatGPT / uzak).\n\n"
        "> Bilgiler yalnızca eğitim amaçlıdır, tıbbi tavsiye değildir."
    )


@mcp.resource("info://kaynaklar")
def resource_sources() -> str:
    """Veri kaynakları ve ne için kullanıldıkları."""
    return (
        "# Veri Kaynakları\n"
        "- **openFDA** — ilaç etiketleri, etkileşimler, yan etkiler (FAERS).\n"
        "- **NLM RxClass** — ilaç sınıfları (ATC dahil).\n"
        "- **PubMed (NCBI)** — tıbbi literatür.\n"
        "- **DDInter 2.0** — ikili ilaç-ilaç etkileşim şiddeti (CC BY-NC-SA 4.0).\n"
        "- **TİTCK SKRS** — Türk ruhsatlı ilaç kaydı (ad, barkod, ATC, firma, reçete).\n"
        "- **SGK EK-4/A** — geri ödeme, eşdeğer grup, barkod, kamu no.\n"
        "- **TİTCK güvenlik** — ek izleme (dinamikmodul/57) + ruhsat iptali (dinamikmodul/76).\n"
        "- **TİTCK yurt dışı** — yurt dışından temin edilebilen etkin maddeler (dinamikmodul/126)."
    )


@mcp.resource("info://surumler")
def resource_versions() -> str:
    """Paketlenmiş yerel veri kümelerinin sürüm ve kayıt sayıları."""
    titck_meta, sgk_meta = titck.meta(), sgk.meta()
    safety_meta = safety.meta()
    foreign_meta = foreign.meta()
    ddi_meta = interactions.meta()
    monitoring = safety_meta.get("monitoring", {})
    cancellations = safety_meta.get("cancellations", {})
    lines = [
        "# Yerel Veri Sürümleri",
        "| Veri kümesi | Sürüm | Kayıt |",
        "| --- | --- | ---: |",
        f"| TİTCK SKRS | {titck_meta.get('version', '?')} | {titck_meta.get('count', '?')} |",
        f"| SGK EK-4/A | {sgk_meta.get('version', '?')} | {sgk_meta.get('count', '?')} |",
        f"| Ek izleme | {monitoring.get('version', '?')} | {monitoring.get('count', '?')} |",
        f"| Ruhsat iptali | {cancellations.get('version', '?')} | {cancellations.get('count', '?')} |",
        f"| Yurt dışı etkin madde | {foreign_meta.get('version', '?')} | {foreign_meta.get('count', '?')} |",
        f"| DDInter etkileşim | {ddi_meta.get('version', '?')} | {ddi_meta.get('pair_count', '?')} |",
    ]
    return "\n".join(lines)
