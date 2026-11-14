$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $Root "web"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "=== DONMULWON 2 · LINK SHARE MODE ===" -ForegroundColor Cyan
Write-Host "Public link access: anyone who has the URL can open the market-only share app." -ForegroundColor Yellow
Write-Host "Toss account endpoints remain blocked in the share API." -ForegroundColor Green
Set-Location $Root

if (-not (Test-Path $VenvPython)) {
    python -m venv (Join-Path $Root ".venv")
}

$PythonCheck = & $VenvPython -c "import fastapi, uvicorn, pandas, pykrx, yfinance" 2>&1
if ($LASTEXITCODE -ne 0) {
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm was not found. Install Node.js LTS first."
}
if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    Push-Location $WebDir
    npm install
    $NpmExit = $LASTEXITCODE
    Pop-Location
    if ($NpmExit -ne 0) { throw "Web dependency installation failed." }
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing Cloudflare Tunnel (cloudflared)..."
        winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "cloudflared installation failed. Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ and rerun this script."
        }
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    }
}
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared was not found. Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ and rerun this script."
}

Write-Host "Starting isolated share API on 127.0.0.1:8001..."
$ShareDb = Join-Path $Root "data\donmulwon2_share.db"
$BackendCommand = "`$env:DONMULWON_SHARE_MODE='1'; `$env:DONMULWON_DB_PATH='$ShareDb'; & '$VenvPython' -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8001"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $BackendCommand) -WorkingDirectory $Root

Write-Host "Starting friend-share website on 127.0.0.1:5174..."
$FrontendCommand = "npm run dev -- --config vite.share.config.ts"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $FrontendCommand) -WorkingDirectory $WebDir

Start-Sleep -Seconds 6
Start-Process "http://127.0.0.1:5174"

Write-Host ""
Write-Host "Starting Cloudflare Quick Tunnel..." -ForegroundColor Cyan
Write-Host "A public trycloudflare.com link will appear below." -ForegroundColor Green
Write-Host "Send that link only to your friend. Anyone who gets the link can access it." -ForegroundColor Yellow
Write-Host "The link changes whenever this tunnel is restarted." -ForegroundColor Yellow
Write-Host "Press Ctrl+C here to stop external access."
Write-Host ""

& cloudflared tunnel --url http://127.0.0.1:5174
