"""Health & medication information MCP server.

Exposes official US public-health data sources (openFDA, NLM RxNorm) as MCP
tools that Claude, ChatGPT and other MCP clients can call.
"""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import clinical, prices, safety, sgk, titck
from .clients import openfda, pubmed, rxnorm
from .clients.http import APIError

mcp = FastMCP(
    name="Klinik MCP",
    instructions=(
        "Klinik MCP — drug & clinical information tools for Turkish physicians "
        "and pharmacists. Capabilities: (1) openFDA drug labels, adverse events "
        "(FAERS) and recalls, plus condition\u2192drug reverse lookup; (2) NLM "
        "RxNorm/RxClass for name normalization, ingredients/brands and "
        "therapeutic/ATC/mechanism classes; (3) PubMed medical-literature "
        "search; (4) clinical calculators (Cockcroft\u2013Gault creatinine "
        "clearance, Mosteller body-surface-area, weight-based pediatric dose); "
        "(5) Turkey-specific data \u2014 T\u0130TCK SKRS drug registry (search by "
        "name, full info, drugs sharing an ATC code), T\u0130TCK safety status "
        "(additional monitoring \u25bc and authorization cancellations), SGK "
        "EK-4/A bioequivalents & reimbursement status, and TL prices when a "
        "price source is loaded. "
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


def _concepts_by_tty(related_group: dict, tty: str) -> list[str]:
    names: list[str] = []
    for group in related_group.get("conceptGroup", []):
        if group.get("tty") == tty:
            for concept in group.get("conceptProperties", []):
                name = concept.get("name")
                if name:
                    names.append(name)
    return names


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool
async def search_drugs(query: str, max_results: int = 10) -> str:
    """Search for drugs by brand, generic, or even misspelled name.

    Returns matching RxNorm concepts with their RxCUI identifier, term type
    and match score. Use this first to resolve an exact drug name before
    calling the other tools.
    """
    term = _clean(query)
    if not term:
        return "Lütfen aranacak bir ilaç adı girin."
    try:
        candidates = await rxnorm.approximate_term(term, max_entries=max_results * 2)
    except APIError as exc:
        return f"Arama başarısız oldu: {exc}"
    if not candidates:
        return f"'{query}' için eşleşen ilaç bulunamadı."

    seen: set[str] = set()
    picked: list[tuple[str, str]] = []
    for candidate in candidates:
        rxcui = candidate.get("rxcui")
        if rxcui and rxcui not in seen:
            seen.add(rxcui)
            picked.append((rxcui, candidate.get("score", "")))
        if len(picked) >= max_results:
            break

    prop_results = await asyncio.gather(
        *(rxnorm.properties(rxcui) for rxcui, _ in picked),
        return_exceptions=True,
    )

    lines = [f"## '{query}' için ilaç sonuçları\n"]
    for (rxcui, score), props in zip(picked, prop_results):
        if isinstance(props, Exception) or not props:
            continue
        name = props.get("name", "?")
        tty = props.get("tty", "")
        try:
            score_str = f"{float(score):.0f}"
        except (TypeError, ValueError):
            score_str = str(score)
        lines.append(f"- **{name}** — RxCUI `{rxcui}`, tür: {tty}, skor: {score_str}")
    if len(lines) == 1:
        return f"'{query}' için ayrıntı alınamadı."
    return "\n".join(lines) + DISCLAIMER


@mcp.tool
async def get_drug_label(drug_name: str) -> str:
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


@mcp.tool
async def get_drug_interactions(drug_name: str) -> str:
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


@mcp.tool
async def get_drug_adverse_events(drug_name: str, limit: int = 10) -> str:
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


@mcp.tool
async def get_drug_recalls(query: str, limit: int = 10) -> str:
    """Get drug recall / enforcement reports for a product from openFDA."""
    term = _clean(query)
    if not term:
        return "Lütfen bir ilaç/ürün adı girin."
    try:
        results = await openfda.enforcement_reports(term, limit=limit)
    except APIError as exc:
        return f"openFDA isteği başarısız oldu: {exc}"
    if not results:
        return f"'{query}' için geri çağırma (recall) kaydı bulunamadı."

    blocks = [f"# {query} — Geri Çağırma (Recall) Kayıtları\n"]
    for report in results:
        product = _join(report.get("product_description"))[:160]
        blocks.append(
            f"### {product}\n"
            f"- **Sınıf:** {report.get('classification', '?')}\n"
            f"- **Durum:** {report.get('status', '?')}\n"
            f"- **Sebep:** {_truncate(_join(report.get('reason_for_recall')), 300)}\n"
            f"- **Firma:** {report.get('recalling_firm', '?')}\n"
            f"- **Başlangıç tarihi:** {_fmt_date(report.get('recall_initiation_date'))}"
        )
    return "\n\n".join(blocks) + DISCLAIMER


@mcp.tool
async def get_rxnorm_details(drug_name: str) -> str:
    """Normalize a drug name and list its ingredients and brand names (RxNorm)."""
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
        rxcui = ids[0]
        props, related_group = await asyncio.gather(
            rxnorm.properties(rxcui),
            rxnorm.related(rxcui, ["IN", "BN"]),
        )
    except APIError as exc:
        return f"RxNorm isteği başarısız oldu: {exc}"

    ingredients = _concepts_by_tty(related_group, "IN")
    brands = _concepts_by_tty(related_group, "BN")
    lines = [
        f"# {props.get('name', drug_name)} — RxNorm",
        f"**RxCUI:** `{rxcui}`",
    ]
    if props.get("tty"):
        lines.append(f"**Tür (TTY):** {props['tty']}")
    if ingredients:
        lines.append(f"**Etken maddeler:** {', '.join(sorted(set(ingredients)))}")
    if brands:
        lines.append(f"**Marka adları:** {', '.join(sorted(set(brands))[:25])}")
    return "\n".join(lines) + DISCLAIMER


@mcp.tool
async def find_drugs_for_condition(condition: str, max_results: int = 10) -> str:
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


@mcp.tool
async def get_drug_classes(drug_name: str) -> str:
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


@mcp.tool
async def search_medical_literature(query: str, max_results: int = 10) -> str:
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


@mcp.tool
def creatinine_clearance(
    age: float, weight_kg: float, serum_creatinine_mg_dl: float, sex: str
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


@mcp.tool
def body_surface_area(height_cm: float, weight_kg: float) -> str:
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


@mcp.tool
def pediatric_dose(
    weight_kg: float,
    mg_per_kg_per_day: float,
    doses_per_day: int = 1,
    max_mg_per_day: float | None = None,
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


@mcp.tool
def find_drug_equivalents(drug: str, max_results: int = 25) -> str:
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
    members = sgk.group_members(group)
    has_price = prices.available()
    if has_price:
        members = sorted(
            members,
            key=lambda m: prices.retail(m.get("barcode"))
            if prices.retail(m.get("barcode")) is not None
            else float("inf"),
        )
    members = members[:max_results]
    note = " (fiyata göre, ucuzdan)" if has_price else ""
    lines = [
        f"# {record.get('name')} — Eşdeğer İlaçlar",
        f"**Eşdeğer grup:** `{group}` · **{len(members)}** ürün{note}\n",
        "| İlaç | Barkod | Fiyat (TL) |" if has_price else "| İlaç | Barkod |",
        "| --- | --- | ---: |" if has_price else "| --- | --- |",
    ]
    for member in members:
        if has_price:
            value = prices.retail(member.get("barcode"))
            price_s = f"{value:.2f}" if value is not None else "—"
            lines.append(
                f"| {member.get('name', '?')} | {member.get('barcode', '?')} | {price_s} |"
            )
        else:
            lines.append(
                f"| {member.get('name', '?')} | {member.get('barcode', '?')} |"
            )
    return "\n".join(lines) + _sgk_disclaimer()


@mcp.tool
def get_reimbursement_status(drug: str) -> str:
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


@mcp.tool
def search_turkish_drugs(query: str, max_results: int = 15) -> str:
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


@mcp.tool
def get_turkish_drug_info(query: str) -> str:
    """Get full TİTCK registry info for a Turkish drug by name or barcode."""
    drug = titck.resolve(query)
    if not drug:
        return f"'{query}' TİTCK listesinde bulunamadı."
    lines = [f"# {drug.get('name')}", *_titck_fields(drug)]
    price = prices.retail(drug.get("barcode"))
    if price is not None:
        suffix = " *(örnek)*" if prices.meta().get("sample") else ""
        lines.append(f"- **Perakende fiyat:** {price:.2f} TL{suffix}")
    lines.extend(_safety_lines(drug))
    return "\n".join(lines) + _titck_disclaimer()


@mcp.tool
def find_drugs_by_active_ingredient(query: str, max_results: int = 30) -> str:
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


@mcp.tool
def get_drug_safety_status(query: str) -> str:
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
# Price tool (pluggable barcode->TL source; see prices.py / build_prices.py)
# --------------------------------------------------------------------------- #
def _price_disclaimer() -> str:
    info = prices.meta()
    if info.get("sample"):
        return (
            "\n\n> ⚠️ **ÖRNEK FİYAT** (gerçek değil). Gerçek fiyat için "
            "`scripts/build_prices.py` ile ticari bir barkod→TL dışa aktarımı "
            "yükleyin.\n\n---\n*Fiyat kaynağı: " + str(info.get("source", "?")) + "*"
        )
    return (
        f"\n\n---\n*Fiyat kaynağı: {info.get('source', '?')} "
        f"({info.get('version', '?')}). Güncellik için kaynaktan teyit edin.*"
    )


@mcp.tool
def get_drug_price(query: str) -> str:
    """Get the TL price (retail/depot) for a Turkish drug by name or barcode.

    Prices come from a pluggable commercial/pharmacy export loaded into
    data/prices.json; if none is configured the tool says so.
    """
    if not prices.available():
        return (
            "Fiyat veri kaynağı yüklü değil. Ticari/eczane bir barkod→TL fiyat "
            "dışa aktarımını `scripts/build_prices.py` ile ekleyin (bkz. README)."
        )
    drug = titck.resolve(query)
    barcode = (
        drug.get("barcode")
        if drug
        else (query.strip() if query.strip().isdigit() else None)
    )
    name = drug.get("name") if drug else query
    entry = prices.lookup(barcode)
    if not entry:
        return f"'{query}' için fiyat bulunamadı."
    lines = [f"# {name} — Fiyat"]
    if barcode:
        lines.append(f"- **Barkod:** {barcode}")
    if entry.get("retail") is not None:
        lines.append(f"- **Perakende (KDV dahil):** {entry['retail']:.2f} TL")
    if entry.get("depot") is not None:
        lines.append(f"- **Depocu satış:** {entry['depot']:.2f} TL")
    return "\n".join(lines) + _price_disclaimer()


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
