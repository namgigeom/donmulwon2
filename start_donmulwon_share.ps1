$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $Root "web"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "=== DONMULWON 2 · PRIVATE SHARE MODE ===" -ForegroundColor Cyan
Write-Host "Share mode blocks every /api/toss* account endpoint." -ForegroundColor Yellow
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

Write-Host "Starting isolated share API on 127.0.0.1:8001..."
$ShareDb = Join-Path $Root "data\donmulwon2_share.db"
$BackendCommand = "`$env:DONMULWON_SHARE_MODE='1'; `$env:DONMULWON_DB_PATH='$ShareDb'; & '$VenvPython' -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8001"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $BackendCommand) -WorkingDirectory $Root

Write-Host "Starting friend-share website on 127.0.0.1:5174..."
$FrontendCommand = "npm run dev -- --config vite.share.config.ts"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $FrontendCommand) -WorkingDirectory $WebDir

Start-Sleep -Seconds 5
Start-Process "http://127.0.0.1:5174"

Write-Host ""
Write-Host "Local share preview: http://127.0.0.1:5174" -ForegroundColor Green
Write-Host "Share API health:    http://127.0.0.1:8001/api/health"
Write-Host "Toss endpoints in share mode must return HTTP 404."
Write-Host ""

$Tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if ($Tailscale) {
    Write-Host "Enabling private HTTPS access through Tailscale Serve..."
    $ServeOutput = & tailscale serve --bg 5174 2>&1
    $ServeExit = $LASTEXITCODE
    $ServeOutput | ForEach-Object { Write-Host $_ }
    if ($ServeExit -eq 0) {
        Write-Host ""
        Write-Host "Share the displayed https://...ts.net address only with the invited friend." -ForegroundColor Green
    } else {
        Write-Host "Tailscale Serve did not start. Connect Tailscale, then run: tailscale serve --bg 5174" -ForegroundColor Yellow
    }
} else {
    Write-Host "Tailscale is not installed or not on PATH." -ForegroundColor Yellow
    Write-Host "Install Tailscale on this PC and your friend's device, sign in, and invite only that one friend."
    Write-Host "Then run: tailscale serve --bg 5174"
}

Write-Host ""
Write-Host "Keep this PC, the API window, the website window, and Tailscale running."
