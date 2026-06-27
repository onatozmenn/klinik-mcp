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
  <b>Türk hekim ve eczacılar için ilaç &amp; klinik bilgi MCP sunucusu.</b><br>
  TİTCK · SGK EK-4/A · openFDA · NLM RxClass · PubMed — tek araç setinde;
  Claude ve ChatGPT ile çalışır.
</p>

<p align="center">
  <a href="https://smithery.ai/server/onatozmen44/klinik-mcp"><img alt="Smithery" src="https://img.shields.io/badge/Smithery-listed-ea580c"></a>
  <a href="https://github.com/onatozmenn/klinik-mcp"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-source-181717?logo=github"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-22c55e"></a>
  <img alt="MCP" src="https://img.shields.io/badge/MCP-stdio%20%7C%20HTTP-2563eb">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
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
<summary><b>16 araç — tam listeyi açmak için tıkla</b></summary>

| Araç | Açıklama | Kaynak |
| --- | --- | --- |
| `get_drug_label` | Endikasyon, doz, uyarı, kontrendikasyon, etkileşim, yan etki | openFDA |
| `get_drug_interactions` | Etiketteki ilaç etkileşimleri bölümü | openFDA |
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
3. Kaydet. Artık sohbette _“parol muadili nedir, en ucuzu hangisi?”_ gibi sorabilirsin.

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
