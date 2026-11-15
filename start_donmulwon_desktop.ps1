$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $Root "web"
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Log = Join-Path $Root "logs"
$Data = Join-Path $Root "data"
$Started = @()
function Q([string]$s) { "'" + $s.Replace("'","''") + "'" }
function Start-Hidden([string]$Name,[string]$Command) {
  # Start-Process의 ArgumentList는 인자 배열을 하나의 문자열로 합치므로
  # 경로의 따옴표가 깨질 수 있다. UTF-16LE Base64 명령으로 전달해 공백/드라이브 문자를 보호한다.
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
  $p=Start-Process powershell.exe -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-EncodedCommand",$encoded) -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  $script:Started += [pscustomobject]@{Name=$Name;Id=$p.Id}
  Write-Host "$Name 시작" -ForegroundColor DarkGray
}
function Stop-All {
  foreach($item in @($script:Started)) { try { taskkill.exe /PID $item.Id /T /F 2>$null | Out-Null } catch {} }
}
try {
  Clear-Host
  Write-Host "DONMULWON 2 - 개인 사이트 + 친구 공유" -ForegroundColor Cyan
  if(!(Test-Path $Py)){
    Write-Host "프로젝트 Python 가상환경 생성 중..." -ForegroundColor Yellow
    python -m venv (Join-Path $Root ".venv")
  }
  if(!(Test-Path $Py)){throw "Python 가상환경 생성에 실패했습니다. Python 설치를 확인하세요."}
  if(!(Get-Command npm -ErrorAction SilentlyContinue)){throw "Node.js/npm을 찾을 수 없습니다. Node.js LTS를 설치하세요."}

  Write-Host "실행 환경 확인 중..." -ForegroundColor Yellow
  & $Py -c "import fastapi, uvicorn, pandas, pykrx, yfinance"
  if($LASTEXITCODE -ne 0){
    & $Py -m pip install --upgrade pip
    & $Py -m pip install -r (Join-Path $Root "requirements.txt")
    if($LASTEXITCODE -ne 0){throw "Python 패키지 설치에 실패했습니다."}
  }
  if(!(Test-Path (Join-Path $WebDir "node_modules"))){
    Push-Location $WebDir
    npm install
    $npmExit=$LASTEXITCODE
    Pop-Location
    if($npmExit -ne 0){throw "웹 패키지 설치에 실패했습니다."}
  }
  if(!(Get-Command cloudflared -ErrorAction SilentlyContinue)){
    if(Get-Command winget -ErrorAction SilentlyContinue){
      Write-Host "Cloudflare Tunnel 설치 중..." -ForegroundColor Yellow
      winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
      if($LASTEXITCODE -ne 0){throw "cloudflared 설치에 실패했습니다. Cloudflare 공식 설치 페이지에서 설치하세요."}
      $env:Path=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")
    }
  }
  if(!(Get-Command cloudflared -ErrorAction SilentlyContinue)){throw "cloudflared를 찾을 수 없습니다. Cloudflare 공식 설치 페이지에서 설치 후 다시 실행하세요."}
  foreach($port in @(5173,5174,8000,8001)){
    if(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue){throw "포트 $port 가 이미 사용 중입니다. 기존 서버를 종료하세요."}
  }
  New-Item -ItemType Directory -Force -Path $Log,$Data | Out-Null
  $out=Join-Path $Log "cloudflared.stdout.log"
  $err=Join-Path $Log "cloudflared.stderr.log"
  Remove-Item $out,$err -Force -ErrorAction SilentlyContinue
  $py=Q $Py; $root=Q $Root; $web=Q $WebDir; $db=Q (Join-Path $Data "donmulwon2_share.db")
  Write-Host "[1/4] 개인 사이트 시작" -ForegroundColor Yellow
  Start-Hidden "개인 API" "Set-Location $root; & $py -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8000"
  Start-Hidden "개인 웹" "Set-Location $web; npm run dev -- --host 127.0.0.1 --strictPort"
  Write-Host "[2/4] 친구 공유 사이트 시작" -ForegroundColor Yellow
  $shareCmd='$env:DONMULWON_SHARE_MODE=''1''; $env:DONMULWON_DB_PATH='+$db+'; Set-Location '+$root+'; & '+$py+' -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8001'
  Start-Hidden "공유 API" $shareCmd
  Start-Hidden "공유 웹" "Set-Location $web; npm run dev -- --config vite.share.config.ts"
  Write-Host "[3/4] 로컬 서버 확인" -ForegroundColor Yellow
  $ready=$false
  for($i=0;$i -lt 45;$i++){
    try{
      $a=Invoke-RestMethod "http://127.0.0.1:8000/api/health" -TimeoutSec 2
      $b=Invoke-RestMethod "http://127.0.0.1:8001/api/health" -TimeoutSec 2
      $c=Invoke-WebRequest "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing
      $d=Invoke-WebRequest "http://127.0.0.1:5174" -TimeoutSec 2 -UseBasicParsing
      if($a.ok -and $b.ok -and $c.StatusCode -eq 200 -and $d.StatusCode -eq 200){$ready=$true;break}
    }catch{}
    Start-Sleep 2
  }
  if(!$ready){throw "웹/API 서버가 준비되지 않았습니다. logs 폴더를 확인하세요."}
  Write-Host "[4/4] Cloudflare 공개 링크 생성" -ForegroundColor Yellow
  $cf=(Get-Command cloudflared).Source
  $t=Start-Process $cf -ArgumentList @("tunnel","--no-autoupdate","--url","http://127.0.0.1:5174") -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  $script:Started += [pscustomobject]@{Name="Cloudflare Tunnel";Id=$t.Id}
  $url=$null
  for($i=0;$i -lt 60;$i++){
    if($t.HasExited){throw "Cloudflare Tunnel이 종료됐습니다. logs/cloudflared.stderr.log를 확인하세요."}
    foreach($f in @($out,$err)){
      if(Test-Path $f){$logText=Get-Content $f -Raw -ErrorAction SilentlyContinue;if($logText -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com"){$url=$Matches[0];break}}
    }
    if($url){break}
    Start-Sleep 1
  }
  if(!$url){throw "공개 주소를 받지 못했습니다. logs/cloudflared.*.log를 확인하세요."}
  Start-Process "http://127.0.0.1:5173"
  try{Set-Clipboard $url}catch{}
  Write-Host ""
  Write-Host "내 사이트: http://127.0.0.1:5173" -ForegroundColor Cyan
  Write-Host "친구 링크: $url" -ForegroundColor Yellow
  Write-Host "링크는 클립보드에도 복사했습니다." -ForegroundColor Green
  Write-Host "이 창에서 Enter 또는 Ctrl+C를 누르면 전체 종료됩니다."
  Write-Host "PC가 켜져 있고 실행 창이 유지될 때만 친구가 접속할 수 있습니다."
  [void](Read-Host "종료하려면 Enter")
}catch{
  Write-Host "[오류] $($_.Exception.Message)" -ForegroundColor Red
  [void](Read-Host "Enter를 누르면 서버를 정리합니다")
}finally{
  Write-Host "서버와 터널 종료 중..." -ForegroundColor Yellow
  Stop-All
  Write-Host "종료 완료." -ForegroundColor Green
  Start-Sleep 2
}