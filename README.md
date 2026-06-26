---
title: Klinik MCP
emoji: 💊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
pinned: false
---

# Klinik MCP

Bir **MCP (Model Context Protocol) sunucusu** — Türk hekim ve eczacılar için.
Resmî, ücretsiz ve çoğunlukla API anahtarı gerektirmeyen veri kaynaklarını
— **TİTCK SKRS** ve **SGK EK-4/A** (Türkiye) ile **openFDA**, **NLM
RxNorm/RxClass** ve **PubMed** (uluslararası) — büyük dil modellerine **araç
(tool)** olarak açar; ayrıca klinik hesaplayıcılar (kreatinin klerensi, VYA,
pediatrik doz) içerir. Hem **Claude Desktop** (stdio) hem de **ChatGPT** (HTTP
connector) ile çalışır.

> ⚠️ **Sorumluluk reddi:** Bu sunucunun sağladığı bilgiler yalnızca eğitim
> amaçlıdır ve **tıbbi tavsiye değildir**. Tıbbi kararlar için mutlaka bir
> sağlık profesyoneline danışın.

## Araçlar (Tools)

| Araç | Açıklama | Kaynak |
| --- | --- | --- |
| `search_drugs` | İlaç adıyla (yanlış yazımlar dâhil) arama, RxCUI çözümleme | RxNorm |
| `get_drug_label` | Endikasyon, doz, uyarı, kontrendikasyon, etkileşim, yan etki | openFDA |
| `get_drug_interactions` | Etiketteki ilaç etkileşimleri bölümü | openFDA |
| `get_drug_adverse_events` | En sık bildirilen yan etkiler (FAERS) | openFDA |
| `get_drug_recalls` | Geri çağırma (recall) kayıtları | openFDA |
| `get_rxnorm_details` | Normalleştirme: etken madde ve marka adları | RxNorm |
| `find_drugs_for_condition` | Hastalığa göre ilaç bulma (ters arama) | openFDA |
| `get_drug_classes` | Terapötik / ATC / etki mekanizması sınıfları | RxClass |
| `search_medical_literature` | PubMed'de tıbbi literatür araması | PubMed |
| `creatinine_clearance` | Kreatinin klerensi (Cockcroft–Gault) | Formül |
| `body_surface_area` | Vücut yüzey alanı (Mosteller) | Formül |
| `pediatric_dose` | Kilo bazlı pediatrik doz hesabı | Formül |
| `find_drug_equivalents` | Eşdeğer (muadil) grup + fiyat (en ucuz) | SGK EK-4/A |
| `get_reimbursement_status` | Geri ödeme durumu (listede mi) | SGK EK-4/A |
| `search_turkish_drugs` | Türk ilaç kaydı arama (ad) | TİTCK SKRS |
| `get_turkish_drug_info` | İlaç bilgisi: ATC, firma, reçete türü | TİTCK SKRS |
| `find_drugs_by_active_ingredient` | Aynı ATC (etkin madde) ilaçlar | TİTCK SKRS |
| `get_drug_safety_status` | Ek izleme (▼) + ruhsat iptali | TİTCK |
| `get_drug_price` | TL fiyat (perakende/depocu) | Ticari export |

## Kurulum

```powershell
# Proje klasöründe
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

İsteğe bağlı olarak `.env.example` dosyasını `.env` olarak kopyalayıp
`OPENFDA_API_KEY` girerek hız limitlerini yükseltebilirsiniz (gerekli değildir).

## Çalıştırma

**stdio (yerel istemciler / Claude Desktop):**

```powershell
.\.venv\Scripts\python.exe -m health_mcp
```

**HTTP (ChatGPT connector / uzak istemciler):**

```powershell
.\.venv\Scripts\python.exe -m health_mcp --transport http --port 8000
```

## Claude Desktop'a bağlama

`claude_desktop_config.json` dosyasına ekleyin
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "klinik": {
      "command": "C:\\Users\\onat\\OneDrive\\Desktop\\KlinikMCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "health_mcp"]
    }
  }
}
```

Claude Desktop'ı yeniden başlatın; araçlar araç (🔨) menüsünde görünür.

## ChatGPT'ye bağlama

1. Sunucuyu HTTP modunda çalıştırın (yukarıdaki komut).
2. Yerelse, dışarıya açmak için bir tünel kurun (ör. `ngrok http 8000`).
3. ChatGPT → **Settings → Connectors → Advanced → Developer mode** açın.
4. Yeni connector ekleyin ve MCP uç noktasını girin:
   `https://<tünel-adresiniz>/mcp/`

> Not: ChatGPT'de özel MCP araçları, **Developer mode** (geliştirici modu)
> etkin olan hesaplarda kullanılabilir.

## Test (MCP Inspector)

```powershell
npx @modelcontextprotocol/inspector .\.venv\Scripts\python.exe -m health_mcp
```

## Veri kaynakları

- **openFDA** — https://open.fda.gov/apis/ (ilaç etiketleri, yan etkiler, geri çağırmalar)
- **NLM RxNorm / RxNav / RxClass** — https://rxnav.nlm.nih.gov/ (ilaç terminolojisi ve sınıfları)
- **PubMed (NCBI E-utilities)** — https://www.ncbi.nlm.nih.gov/books/NBK25500/ (tıbbi literatür)

## 🇹🇷 Türkiye verisi (SGK EK-4/A — tam liste)

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

## 🇹🇷 Tam ilaç kaydı (TİTCK SKRS)

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

## �️ TİTCK güvenlik durumu (ek izleme + ruhsat iptali)

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

## �🔄 Otomatik güncelleme

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

## 💰 TL fiyatı (takılabilir entegrasyon)

Net TL perakende fiyatı **ücretsiz/public olarak yok** (SGK EK-4/A iskonto oranı,
TİTCK yalnızca EUR referans). Bu yüzden fiyat **takılabilir** bir kaynaktan gelir:
`get_drug_price` ve `find_drug_equivalents` (en ucuz eşdeğer), barkod→TL fiyatı
[src/health_mcp/data/prices.json](src/health_mcp/data/prices.json)'dan okur.

Varsayılan olarak **fiyat verisi gelmez** — hiçbir sahte değer gösterilmez; gerçek
bir kaynak yüklenene kadar araçlar fiyatı sessizce atlar. Gerçek fiyatı yüklemek
için herhangi bir ticari/eczane kaynağından (Rxmediapharma, eczane otomasyonu,
ticari CSV) **barkod + perakende fiyat** dışa aktarıp:

```powershell
.\.venv\Scripts\python.exe scripts/build_prices.py "C:\yol\fiyatlar.csv" --source "Rxmediapharma" --version 2026-06
```

Script barkod/perakende/depocu sütunlarını otomatik bulur (CSV veya Excel). Fiyat
kaynağı yoksa araçlar fiyatı sessizce atlar.
