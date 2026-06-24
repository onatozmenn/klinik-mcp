# start_mcp.ps1 — health-mcp'yi KALICI ngrok dev domain ile tek komutla başlatır.
#
# Kullanım:
#   1) https://dashboard.ngrok.com/domains adresinden hesabının kalıcı dev
#      domain'ini kopyala (ör. "cuddly-otter-1234.ngrok-free.app").
#   2) Aşağıdaki $Domain satırını kendi domain'inle değiştir.
#   3) Bu dosyaya sağ tıkla > "Run with PowerShell"  (veya terminalde:
#      powershell -ExecutionPolicy Bypass -File scripts\start_mcp.ps1)
#
# Sonuç: MCP sunucusu + ngrok ayrı pencerelerde açılır, URL hep aynı kalır.

$Domain = "BURAYA-DEV-DOMAIN.ngrok-free.app"   # <-- SADECE BUNU DEĞİŞTİR

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot          # repo kökü (scripts/'in bir üstü)
$Py   = Join-Path $Root ".venv\Scripts\python.exe"
$Port = 8000

if ($Domain -like "BURAYA-*") {
    Write-Host "Önce script içindeki `$Domain değerini kendi ngrok dev domain'inle değiştir." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $Py)) { throw "Sanal ortam bulunamadı: $Py" }

# 1) MCP sunucusu (HTTP mod) — ayrı pencerede
Start-Process powershell -WorkingDirectory $Root -ArgumentList @(
    "-NoExit", "-Command",
    "& '$Py' -m health_mcp --transport http --port $Port"
)

# 2) ngrok — sabit dev domain'e bağlı, ayrı pencerede
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "ngrok http $Port --url=https://$Domain"
)

Write-Host ""
Write-Host "MCP sunucusu  : http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "ChatGPT URL'si: https://$Domain/mcp" -ForegroundColor Cyan
Write-Host "(Bu URL artık hiç değişmeyecek — ChatGPT'ye bir kez gir, yeter.)"
