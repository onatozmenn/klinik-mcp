---
title: Klinik MCP
emoji: 💊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
pinned: false
---

<p align="center">
  <img src="KlinikMCP.png" alt="Klinik MCP" width="140">
</p>

<h1 align="center">Klinik MCP</h1>

<p align="center">
  <b>Drug &amp; clinical information MCP server for Turkish physicians and pharmacists.</b><br>
  TİTCK · SGK EK-4/A · openFDA · NLM RxClass · PubMed in a single tool set;
  works with Claude and ChatGPT.
</p>

<p align="center">
  <a href="https://github.com/onatozmenn/klinik-mcp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/onatozmenn/klinik-mcp/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://smithery.ai/server/onatozmen44/klinik-mcp"><img alt="Smithery" src="https://img.shields.io/badge/Smithery-listed-ea580c"></a>
  <a href="https://github.com/onatozmenn/klinik-mcp"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-source-181717?logo=github"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-22c55e"></a>
  <img alt="MCP" src="https://img.shields.io/badge/MCP-stdio%20%7C%20HTTP-2563eb">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
</p>

<p align="center">
  <b>English</b> · <a href="#turkce">Türkçe</a>
</p>

<a name="english"></a>

> ⚠️ **Disclaimer:** Everything this server returns is for educational purposes
> only and is **not medical advice**. Always consult a qualified healthcare
> professional for medical decisions.

## 💬 Example questions

Ask your assistant things like:

- *"What is Parol's SGK equivalent (muadil) and reimbursement status?"* → `find_drug_equivalents`
- *"Is Glioscan under additional monitoring, or has its licence been cancelled?"* → `get_drug_safety_status`
- *"What warnings are on metformin's FDA label?"* → `get_drug_label`
- *"70 years old, 60 kg, creatinine 1.4, female — what is the creatinine clearance?"* → `creatinine_clearance`
- *"TİTCK record for amoxicillin: ATC, company, prescription type?"* → `get_turkish_drug_info`
- *"What is Parol's official patient leaflet (KÜB/KT)?"* → `get_drug_leaflet`
- *"Can amifampridine be supplied from abroad?"* → `find_foreign_supply`
- *"Can warfarin and aspirin be taken together?"* → `check_drug_interactions`

Answers come from **official sources** (TİTCK, SGK, openFDA, NLM, PubMed), not
from the model's training data. Replies are written in Turkish.

**One-click workflows (MCP Prompts):** your client (Claude, Cursor and friends)
shows these as ready-made commands:

- `ilac_bilgisi` — TİTCK record + safety status + SGK equivalents in one summary.
- `muadil_ve_geri_odeme` — SGK reimbursement + equivalent (muadil) group.
- `renal_doz_kontrol` — creatinine clearance plus a renal-dosing reminder.

## 👥 Who is it for?

| User | Start with | Why |
| --- | --- | --- |
| **Physician** | `get_drug_label` · `creatinine_clearance` · `get_drug_safety_status` | Indication/dose/warning + renal dosing + safety flags |
| **Pharmacist** | `find_drug_equivalents` · `get_reimbursement_status` · `get_drug_safety_status` | Equivalents + reimbursement + safety status |
| **Researcher** | `search_medical_literature` · `get_drug_classes` · `find_drugs_for_condition` | PubMed + drug classes + reverse indication lookup |

> This server is **not a clinical decision tool**. Confirming against the
> official source and applying clinical judgement is mandatory.

## Tools

<details>
<summary><b>18 tools — click to expand the full list</b></summary>

| Tool | Description | Source |
| --- | --- | --- |
| `get_drug_label` | Indications, dosage, warnings, contraindications, interactions, adverse reactions | openFDA |
| `get_drug_interactions` | The drug-interactions section of one label | openFDA |
| `check_drug_interactions` | Pairwise interaction severity (Major/Moderate/Minor) | DDInter |
| `get_drug_adverse_events` | Most frequently reported adverse events (FAERS) | openFDA |
| `find_drugs_for_condition` | Drugs indicated for a condition (reverse lookup) | openFDA |
| `get_drug_classes` | Therapeutic / ATC / mechanism-of-action classes | RxClass |
| `search_medical_literature` | Medical literature search on PubMed | PubMed |
| `creatinine_clearance` | Creatinine clearance (Cockcroft–Gault) | Formula |
| `body_surface_area` | Body surface area (Mosteller) | Formula |
| `pediatric_dose` | Weight-based pediatric dose arithmetic | Formula |
| `find_drug_equivalents` | Equivalent (muadil) group | SGK EK-4/A |
| `get_reimbursement_status` | Reimbursement status (is it on the list) | SGK EK-4/A |
| `search_turkish_drugs` | Search the Turkish drug registry by name | TİTCK SKRS |
| `get_turkish_drug_info` | Drug info: ATC, company, prescription type | TİTCK SKRS |
| `get_drug_leaflet` | Official KÜB/KT leaflet links (clinician + patient) | TİTCK |
| `find_drugs_by_active_ingredient` | Drugs sharing the same ATC (active substance) | TİTCK SKRS |
| `find_foreign_supply` | Active substances suppliable from abroad | TİTCK |
| `get_drug_safety_status` | Additional monitoring (▼) + licence cancellation | TİTCK |

</details>

## 🚀 Connecting (no installation required)

The server is **live** (HuggingFace Spaces + Smithery), so most people need no
setup at all. Pick your client:

### ChatGPT

1. In ChatGPT, enable **Settings → Connectors → Advanced → Developer mode**.
2. Choose **Add connector** and enter the MCP URL:
   ```
   https://onatozmenn-klinik-mcp.hf.space/mcp
   ```
3. Save. You can now ask things like _"Can warfarin and aspirin be taken together?"_

> Note: custom MCP tools only show up on accounts with **Developer mode** on.

### Claude Desktop

Add this to `claude_desktop_config.json` (Windows:
`%APPDATA%\Claude\claude_desktop_config.json` · macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "klinik": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://onatozmenn-klinik-mcp.hf.space/mcp"]
    }
  }
}
```

Restart Claude Desktop and the tools appear in the 🔨 menu.

### Claude.ai (web)

Remote MCP connects directly on Pro / Max plans (and Free, one connector):

1. **[Customize → Connectors](https://claude.ai/customize/connectors)** → **"+" → Add custom connector**.
2. Enter the MCP URL (leave the OAuth fields empty, the server needs no key):
   ```
   https://onatozmenn-klinik-mcp.hf.space/mcp
   ```
3. Click **Add**, then enable Klinik MCP from **"+" → Connectors** in the chat.

### Smithery (one command)

```powershell
npx -y @smithery/cli install onatozmen44/klinik-mcp --client claude
```

---

<details>
<summary><b>🛠️ Local development (run it on your own machine)</b></summary>

If you want to run it locally or contribute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .

# stdio (for a local Claude Desktop):
.\.venv\Scripts\python.exe -m health_mcp

# HTTP (for ChatGPT / remote clients):
.\.venv\Scripts\python.exe -m health_mcp --transport http --port 8000
```

Optional: copy `.env.example` to `.env` and set `OPENFDA_API_KEY` /
`NCBI_API_KEY` to raise the upstream rate limits (not required).

To point Claude at your local stdio server, set `command` to your own
`.venv\Scripts\python.exe` path and `args` to `["-m", "health_mcp"]`.

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Try the tools in a browser (MCP Inspector):

```powershell
npx @modelcontextprotocol/inspector .\.venv\Scripts\python.exe -m health_mcp
```

</details>

<details>
<summary><b>📚 Data sources, updating &amp; advanced usage</b></summary>

### Data sources

- **openFDA** — https://open.fda.gov/apis/ (drug labels, adverse events, recalls)
- **NLM RxNorm / RxNav / RxClass** — https://rxnav.nlm.nih.gov/ (drug terminology and classes)
- **PubMed (NCBI E-utilities)** — https://www.ncbi.nlm.nih.gov/books/NBK25500/ (medical literature)
- **DDInter 2.0** — https://ddinter.scbdd.com/ (pairwise drug-drug interactions; CC BY-NC-SA 4.0, non-commercial use only)

### 🇹🇷 Turkish data (SGK EK-4/A, full list)

`find_drug_equivalents` and `get_reimbursement_status` read SGK's **complete**
reimbursement list, "Bedeli Ödenecek İlaçlar Listesi (EK-4/A)" (~8,000 drugs:
**equivalent group, barcode, public number, list-entry date, reimbursement**)
([src/health_mcp/data/sgk_ek4a.json](src/health_mcp/data/sgk_ek4a.json)).

The full list is published publicly inside SGK's consolidated "İşlenmiş Güncel
SUT" zip (`EK-4 LİSTELERİ/EK-4A BEDELİ ÖDENECEK İLAÇLAR LİSTESİ.xlsx`).
`scripts/update_data.py` finds, downloads and processes it automatically.

> **Note on retail prices:** EK-4/A carries barcodes, equivalents and
> reimbursement, but **not the net retail price in TRY** (the price columns are
> discount rates). TİTCK does not publish barcode-level retail prices either
> (`dinamikmodul/100` is EUR reference pricing, without barcodes). A commercial
> drug database is needed for real TRY prices.

Manual update (with an EK-4/A file you extracted from the zip):

```powershell
.\.venv\Scripts\python.exe scripts/build_sgk_snapshot.py "C:\path\EK-4A.xlsx" --version "2026"
```

### 🇹🇷 Full drug registry (TİTCK SKRS)

`search_turkish_drugs`, `get_turkish_drug_info` and
`find_drugs_by_active_ingredient` read **every active product** in the TİTCK
SKRS e-prescription list (~7,900 drugs: name, barcode, ATC, company,
prescription type, essential-medicines flag)
([src/health_mcp/data/titck_drugs.json](src/health_mcp/data/titck_drugs.json)).

To refresh it:

1. Download the latest `.xlsx`: **titck.gov.tr → dinamikmodul/43 "SKRS E-Reçete
   İlaç ve Diğer Farmasötik Ürünler Listesi"**.
2. Build the snapshot:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/build_titck_snapshot.py "C:\path\skrs.xlsx" --version 2026-06-23
```

### 🛡️ TİTCK safety status (additional monitoring + licence cancellation)

`get_drug_safety_status`, and the warning lines inside `get_turkish_drug_info`,
read two official TİTCK lists
([src/health_mcp/data/titck_safety.json](src/health_mcp/data/titck_safety.json)):

- **Drugs under additional monitoring** (▼ black triangle) — TİTCK `dinamikmodul/57`
- **Licence cancellation list** — TİTCK `dinamikmodul/76`

Matching is by drug name / active substance (the barcode is empty in most
cancellation records), so product and presentation differences must be confirmed
against the official list. To refresh, download the latest `.xlsx` files and run:

```powershell
.\.venv\Scripts\python.exe scripts/build_titck_safety_snapshot.py `
  --monitoring "C:\path\ekizleme.xlsx" --cancellations "C:\path\ruhsatiptal.xlsx" `
  --monitoring-version 2025-12-19 --cancellations-version 2026-06-19
```

or let `scripts/update_data.py` below fetch them for you.

### 🔄 Automatic updates

TİTCK republishes its lists regularly. Pull the latest data with **one command**:

```powershell
.\.venv\Scripts\python.exe scripts/update_data.py
```

The script locates and downloads the **TİTCK SKRS** list (`titck_drugs.json`),
the **full SGK EK-4/A** (`sgk_ek4a.json`, from the consolidated SUT zip) and the
**TİTCK safety lists** (`titck_safety.json`: additional monitoring + licence
cancellations), then rebuilds the snapshots.
To schedule it weekly (adjust the paths):

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 03:00 /TN "health-mcp-update" /TR "C:\path\.venv\Scripts\python.exe C:\path\scripts\update_data.py"
```

</details>

---

<a name="turkce"></a>

<h2 align="center">🇹🇷 Türkçe</h2>

<p align="center">
  <b>Türk hekim ve eczacılar için ilaç &amp; klinik bilgi MCP sunucusu.</b><br>
  TİTCK · SGK EK-4/A · openFDA · NLM RxClass · PubMed — tek araç setinde;
  Claude ve ChatGPT ile çalışır.
</p>

<p align="center">
  <a href="#english">English</a> · <b>Türkçe</b>
</p>

> ⚠️ **Sorumluluk reddi:** Bu sunucunun sağladığı bilgiler yalnızca eğitim
> amaçlıdır ve **tıbbi tavsiye değildir**. Tıbbi kararlar için mutlaka bir
> sağlık profesyoneline danışın.

## 💬 Örnek sorular

Asistanına şöyle sor:

- *“Parol'un SGK eşdeğeri (muadil) ve geri ödeme durumu nedir?”* → `find_drug_equivalents`
- *“Glioscan ek izlemede mi, ruhsatı iptal mi?”* → `get_drug_safety_status`
- *“Metformin'in FDA etiketinde uyarılar neler?”* → `get_drug_label`
- *“70 yaş, 60 kg, kreatinin 1.4, kadın — kreatinin klerensi kaç?”* → `creatinine_clearance`
- *“Amoksisilin için TİTCK kaydı: ATC, firma, reçete türü?”* → `get_turkish_drug_info`
- *“Parol'un resmi prospektüsü (KÜB/KT) nedir?”* → `get_drug_leaflet`
- *“Amifampridine yurt dışından temin edilebilir mi?”* → `find_foreign_supply`
- *“Warfarin ile aspirin birlikte verilebilir mi?”* → `check_drug_interactions`

Yanıtlar **resmî kaynaklardan** (TİTCK, SGK, openFDA, NLM, PubMed) gelir —
eğitimden tahmin değil.

**Tek tıkla iş akışları (MCP Prompts):** istemcin (Claude / Cursor vb.) bunları
hazır komut olarak gösterir:

- `ilac_bilgisi` — TİTCK kaydı + güvenlik durumu + SGK eşdeğer, tek özette.
- `muadil_ve_geri_odeme` — SGK geri ödeme + eşdeğer (muadil) grubu.
- `renal_doz_kontrol` — kreatinin klerensi hesabı + böbrek dozu hatırlatması.

## 👥 Kimler için?

| Kullanıcı | Başla | Neden |
| --- | --- | --- |
| **Hekim** | `get_drug_label` · `creatinine_clearance` · `get_drug_safety_status` | Endikasyon/doz/uyarı + böbrek dozu + güvenlik bayrakları |
| **Eczacı** | `find_drug_equivalents` · `get_reimbursement_status` · `get_drug_safety_status` | Muadil + geri ödeme + güvenlik durumu |
| **Araştırmacı** | `search_medical_literature` · `get_drug_classes` · `find_drugs_for_condition` | PubMed + ilaç sınıfları + endikasyon ters arama |

> Bu sunucu bir **klinik karar aracı değildir**; resmî kaynak teyidi ve
> hekim/eczacı muhakemesi şarttır.

## Araçlar (Tools)

<details>
<summary><b>18 araç — tam listeyi açmak için tıkla</b></summary>

| Araç | Açıklama | Kaynak |
| --- | --- | --- |
| `get_drug_label` | Endikasyon, doz, uyarı, kontrendikasyon, etkileşim, yan etki | openFDA |
| `get_drug_interactions` | Etiketteki ilaç etkileşimleri bölümü | openFDA |
| `check_drug_interactions` | İki ilaç arası etkileşim şiddeti (Major/Moderate/Minor) | DDInter |
| `get_drug_adverse_events` | En sık bildirilen yan etkiler (FAERS) | openFDA |
| `find_drugs_for_condition` | Hastalığa göre ilaç bulma (ters arama) | openFDA |
| `get_drug_classes` | Terapötik / ATC / etki mekanizması sınıfları | RxClass |
| `search_medical_literature` | PubMed'de tıbbi literatür araması | PubMed |
| `creatinine_clearance` | Kreatinin klerensi (Cockcroft–Gault) | Formül |
| `body_surface_area` | Vücut yüzey alanı (Mosteller) | Formül |
| `pediatric_dose` | Kilo bazlı pediatrik doz hesabı | Formül |
| `find_drug_equivalents` | Eşdeğer (muadil) grup | SGK EK-4/A |
| `get_reimbursement_status` | Geri ödeme durumu (listede mi) | SGK EK-4/A |
| `search_turkish_drugs` | Türk ilaç kaydı arama (ad) | TİTCK SKRS |
| `get_turkish_drug_info` | İlaç bilgisi: ATC, firma, reçete türü | TİTCK SKRS |
| `get_drug_leaflet` | Resmi KÜB/KT prospektüs linkleri (hekim+hasta) | TİTCK |
| `find_drugs_by_active_ingredient` | Aynı ATC (etkin madde) ilaçlar | TİTCK SKRS |
| `find_foreign_supply` | Yurt dışından temin edilebilen etkin maddeler | TİTCK |
| `get_drug_safety_status` | Ek izleme (▼) + ruhsat iptali | TİTCK |

</details>

## 🚀 Bağlama (kurulum gerekmez)

Sunucu **yayında** (HuggingFace Spaces + Smithery) — çoğu kullanıcı için hiçbir
kurulum gerekmez. İstemcini seç:

### ChatGPT

1. ChatGPT → **Settings → Connectors → Advanced → Developer mode**'u aç.
2. **Add connector** de ve MCP URL'sini gir:
   ```
   https://onatozmenn-klinik-mcp.hf.space/mcp
   ```
3. Kaydet. Artık sohbette _“Warfarin ile aspirin birlikte verilebilir mi?”_ gibi sorabilirsin.

> Not: Özel MCP araçları yalnızca **Developer mode** açık hesaplarda görünür.

### Claude Desktop

`claude_desktop_config.json` dosyasına ekle (Windows:
`%APPDATA%\Claude\claude_desktop_config.json` · macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "klinik": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://onatozmenn-klinik-mcp.hf.space/mcp"]
    }
  }
}
```

Claude Desktop'ı kapat-aç; araçlar 🔨 menüsünde görünür.

### Claude.ai (web)

Pro / Max (ve Free — tek connector) planlarında uzak MCP doğrudan bağlanır:

1. **[Customize → Connectors](https://claude.ai/customize/connectors)** → **“+” → Add custom connector**.
2. MCP URL'sini gir (OAuth alanları boş — sunucu anahtarsız):
   ```
   https://onatozmenn-klinik-mcp.hf.space/mcp
   ```
3. **Add** de; sohbette sol alttaki **“+” → Connectors**'tan Klinik MCP'yi aç.

### Smithery (tek komut)

```powershell
npx -y @smithery/cli install onatozmen44/klinik-mcp --client claude
```

---

<details>
<summary><b>🛠️ Yerel geliştirme (kendi makinende çalıştır)</b></summary>

Kendi makinende çalıştırmak veya katkıda bulunmak istersen:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .

# stdio (yerel Claude Desktop için):
.\.venv\Scripts\python.exe -m health_mcp

# HTTP (ChatGPT / uzak istemciler için):
.\.venv\Scripts\python.exe -m health_mcp --transport http --port 8000
```

İsteğe bağlı: `.env.example`'ı `.env`'e kopyalayıp `OPENFDA_API_KEY` / `NCBI_API_KEY`
girerek API hız limitlerini yükseltebilirsin (gerekli değil).

Yereldeki stdio'yu Claude'a bağlamak istersen config'de `command`'i kendi
`.venv\Scripts\python.exe` yoluna, `args`'ı `["-m", "health_mcp"]`'e ayarla.

Testleri çalıştır:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Araçları tarayıcıda denemek (MCP Inspector):

```powershell
npx @modelcontextprotocol/inspector .\.venv\Scripts\python.exe -m health_mcp
```

</details>

<details>
<summary><b>📚 Veri kaynakları, güncelleme & gelişmiş kullanım</b></summary>

### Veri kaynakları

- **openFDA** — https://open.fda.gov/apis/ (ilaç etiketleri, yan etkiler, geri çağırmalar)
- **NLM RxNorm / RxNav / RxClass** — https://rxnav.nlm.nih.gov/ (ilaç terminolojisi ve sınıfları)
- **PubMed (NCBI E-utilities)** — https://www.ncbi.nlm.nih.gov/books/NBK25500/ (tıbbi literatür)
- **DDInter 2.0** — https://ddinter.scbdd.com/ (ikili ilaç-ilaç etkileşim; CC BY-NC-SA 4.0, yalnızca ticari olmayan kullanım)

### 🇹🇷 Türkiye verisi (SGK EK-4/A — tam liste)

`find_drug_equivalents` ve `get_reimbursement_status` araçları, SGK'nın **tam**
"Bedeli Ödenecek İlaçlar Listesi (EK-4/A)"sını okur (~8.000 ilaç: **eşdeğer grup,
barkod, kamu no, listeye giriş tarihi, geri ödeme**)
([src/health_mcp/data/sgk_ek4a.json](src/health_mcp/data/sgk_ek4a.json)).

Tam liste, SGK'nın **konsolide "İşlenmiş Güncel SUT" zip'i** içinde public olarak
yayımlanır (`EK-4 LİSTELERİ/EK-4A BEDELİ ÖDENECEK İLAÇLAR LİSTESİ.xlsx`).
`scripts/update_data.py` bunu otomatik bulur, indirir ve işler.

> **TL fiyatı notu:** EK-4/A barkod + eşdeğer + geri ödeme içerir ama **net TL
> perakende fiyatı içermez** (fiyat sütunları iskonto oranıdır). TİTCK de barkod
> bazlı retail TL fiyatını public yayımlamaz (`dinamikmodul/100` yalnızca EUR
> referans, barkodsuz). Gerçek TL fiyatı için ticari bir ilaç DB'si gerekir.

Manuel güncelleme (zip'ten çıkardığın EK-4/A ile):

```powershell
.\.venv\Scripts\python.exe scripts/build_sgk_snapshot.py "C:\yol\EK-4A.xlsx" --version "2026"
```

### 🇹🇷 Tam ilaç kaydı (TİTCK SKRS)

`search_turkish_drugs`, `get_turkish_drug_info` ve
`find_drugs_by_active_ingredient` araçları, TITCK SKRS E-Reçete listesinin **tüm
aktif ürünlerini** (~7.900 ilaç: ad, barkod, ATC, firma, reçete türü, temel ilaç
listesi) okur
([src/health_mcp/data/titck_drugs.json](src/health_mcp/data/titck_drugs.json)).

Listeyi güncellemek için:

1. En güncel `.xlsx`'i indir: **titck.gov.tr → dinamikmodul/43 "SKRS E-Reçete
   İlaç ve Diğer Farmasötik Ürünler Listesi"**.
2. Snapshot'ı üret:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/build_titck_snapshot.py "C:\yol\skrs.xlsx" --version 2026-06-23
```

### 🛡️ TİTCK güvenlik durumu (ek izleme + ruhsat iptali)

`get_drug_safety_status` aracı ve `get_turkish_drug_info` içindeki uyarı
satırları, iki resmî TİTCK listesini okur
([src/health_mcp/data/titck_safety.json](src/health_mcp/data/titck_safety.json)):

- **Ek İzlemeye Tabi İlaçlar** (▼ kara üçgen) — TİTCK `dinamikmodul/57`
- **Ruhsat İptal Listesi** — TİTCK `dinamikmodul/76`

Eşleşme ilaç adı/etkin madde bazlıdır (ruhsat iptalinde barkod çoğu kayıtta
boştur), bu yüzden ürün/sunum farkları için resmî listeden teyit edilmelidir.
Listeyi güncellemek için en güncel `.xlsx`'leri indirip:

```powershell
.\.venv\Scripts\python.exe scripts/build_titck_safety_snapshot.py `
  --monitoring "C:\yol\ekizleme.xlsx" --cancellations "C:\yol\ruhsatiptal.xlsx" `
  --monitoring-version 2025-12-19 --cancellations-version 2026-06-19
```

veya tek komutla otomatik (aşağıdaki `scripts/update_data.py` bunu da çeker).

### 🔄 Otomatik güncelleme

TİTCK listesi düzenli güncellenir. En güncel veriyi **tek komutla** çek:

```powershell
.\.venv\Scripts\python.exe scripts/update_data.py
```

Script **TİTCK SKRS** listesini (`titck_drugs.json`), SGK **tam EK-4/A**'yı
(`sgk_ek4a.json`, konsolide SUT zip'inden) ve **TİTCK güvenlik listelerini**
(`titck_safety.json`: ek izleme + ruhsat iptali) kendi bulup indirir ve yeniden
üretir.
Haftalık zamanlamak için (yolları kendine göre düzenle):

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 03:00 /TN "health-mcp-update" /TR "C:\yol\.venv\Scripts\python.exe C:\yol\scripts\update_data.py"
```

</details>
