$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $Root "web"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "=== DONMULWON 2 launcher ===" -ForegroundColor Cyan
Set-Location $Root

if (-not (Test-Path $VenvPython)) {
    Write-Host "[1/4] Creating project virtual environment..."
    python -m venv (Join-Path $Root ".venv")
}

Write-Host "[2/4] Checking Python API dependencies..."
$PythonCheck = & $VenvPython -c "import fastapi, uvicorn, pandas, pykrx" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies from requirements.txt..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm was not found. Install the current Node.js LTS version and run this script again."
}

Write-Host "[3/4] Checking web dependencies..."
if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    Push-Location $WebDir
    npm install
    $NpmExit = $LASTEXITCODE
    Pop-Location
    if ($NpmExit -ne 0) { throw "Web dependency installation failed." }
}

Write-Host "[4/4] Starting backend and website..."
$BackendCommand = "& '$VenvPython' -m uvicorn donmulwon2.api:app --reload --host 127.0.0.1 --port 8000"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $BackendCommand) -WorkingDirectory $Root

$FrontendCommand = "npm run dev -- --host 127.0.0.1"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $FrontendCommand) -WorkingDirectory $WebDir

Start-Sleep -Seconds 4
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "DONMULWON 2 should open at http://localhost:5173" -ForegroundColor Green
Write-Host "Backend API: http://127.0.0.1:8000/api/health"
Write-Host "Keep both server windows open while using the website."
