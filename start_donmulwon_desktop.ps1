$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $Root "web"
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Log = Join-Path $Root "logs"
$Data = Join-Path $Root "data"
$ShutdownFlag = Join-Path $Data "shutdown.request"
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
function Close-DonmulwonBrowserWindow {
  # Close only the app-style window titled with the DONMULWON page title.
  # Do not terminate Chrome/Edge processes: the user's other browser windows stay open.
  try {
    $source = @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class DonmulwonWindowCloser {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
  public static void CloseMatching(string fragment) {
    EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
      if (IsWindowVisible(hWnd)) {
        StringBuilder title = new StringBuilder(512);
        GetWindowText(hWnd, title, title.Capacity);
        if (title.ToString().IndexOf(fragment, StringComparison.OrdinalIgnoreCase) >= 0)
          PostMessage(hWnd, 0x0010, IntPtr.Zero, IntPtr.Zero); // WM_CLOSE
      }
      return true;
    }, IntPtr.Zero);
  }
}
"@
    if (-not ("DonmulwonWindowCloser" -as [type])) { Add-Type -TypeDefinition $source }
    [DonmulwonWindowCloser]::CloseMatching("돈물원 2 | DONMULWON")
  } catch {
    Write-Host "돈물원 브라우저 창 자동 닫기 실패: $($_.Exception.Message)" -ForegroundColor DarkYellow
  }
}
function Stop-All {
  Close-DonmulwonBrowserWindow
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
  Remove-Item $ShutdownFlag -Force -ErrorAction SilentlyContinue
  $out=Join-Path $Log "cloudflared.stdout.log"
  $err=Join-Path $Log "cloudflared.stderr.log"
  Remove-Item $out,$err -Force -ErrorAction SilentlyContinue
  # PowerShell 변수는 대소문자를 구분하지 않는다. $root/$py/$web처럼
  # 기존 $Root/$Py/$WebDir와 충돌하는 이름을 쓰지 않는다.
  $pyQ=Q $Py; $rootQ=Q $Root; $webQ=Q $WebDir; $dbQ=Q (Join-Path $Data "donmulwon2_share.db"); $shutdownQ=Q $ShutdownFlag
  Write-Host "[1/4] 개인 사이트 시작" -ForegroundColor Yellow
  $personalApiCmd='$env:DONMULWON_SHUTDOWN_FILE='+$shutdownQ+'; Set-Location '+$rootQ+'; & '+$pyQ+' -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8000'
  Start-Hidden "개인 API" $personalApiCmd
  Start-Hidden "개인 웹" "Set-Location $webQ; npm run dev -- --host 127.0.0.1 --strictPort"
  Write-Host "[2/4] 친구 공유 사이트 시작" -ForegroundColor Yellow
  $shareCmd='$env:DONMULWON_SHARE_MODE=''1''; $env:DONMULWON_DB_PATH='+$dbQ+'; Set-Location '+$rootQ+'; & '+$pyQ+' -m uvicorn donmulwon2.api:app --host 127.0.0.1 --port 8001'
  Start-Hidden "공유 API" $shareCmd
  Start-Hidden "공유 웹" "Set-Location $webQ; npm run dev -- --config vite.share.config.ts"
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
  # Use an isolated browser profile so shutdown closes only this DONMULWON window.
  $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
  # Open DONMULWON as an app-style window using the user's normal browser profile.
  # This keeps existing Chrome tabs/profile available while giving shutdown a separate window to close.
  $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
  $browserCandidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path $programFilesX86 "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $programFilesX86 "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:LOCALAPPDATA "Microsoft\Edge\Application\msedge.exe")
  )
  $browser = $browserCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  if(!$browser){
    $chromeCommand=Get-Command chrome.exe -ErrorAction SilentlyContinue
    $edgeCommand=Get-Command msedge.exe -ErrorAction SilentlyContinue
    if($chromeCommand){$browser=$chromeCommand.Source}elseif($edgeCommand){$browser=$edgeCommand.Source}
  }
  if(!$browser){throw "Google Chrome 또는 Microsoft Edge를 찾을 수 없습니다. 브라우저 설치 후 다시 실행하세요."}
  $browserArgs = '--app=http://127.0.0.1:5173 --no-first-run --no-default-browser-check'
  Start-Process -FilePath $browser -ArgumentList $browserArgs | Out-Null
  try{Set-Clipboard $url}catch{}
  Write-Host ""
  Write-Host "내 사이트: http://127.0.0.1:5173" -ForegroundColor Cyan
  Write-Host "친구 링크: $url" -ForegroundColor Yellow
  Write-Host "링크는 클립보드에도 복사했습니다." -ForegroundColor Green
  Write-Host "이 창에서 Enter 또는 Ctrl+C를 누르면 전체 종료됩니다."
  Write-Host "PC가 켜져 있고 실행 창이 유지될 때만 친구가 접속할 수 있습니다."
  while(!(Test-Path $ShutdownFlag)){ Start-Sleep -Milliseconds 500 }
  Write-Host "사이트에서 전체 종료 요청을 받았습니다." -ForegroundColor Yellow
}catch{
  Write-Host "[오류] $($_.Exception.Message)" -ForegroundColor Red
  [void](Read-Host "Enter를 누르면 서버를 정리합니다")
}finally{
  Write-Host "서버와 터널 종료 중..." -ForegroundColor Yellow
  Stop-All
  Write-Host "종료 완료." -ForegroundColor Green
  Start-Sleep 1
}
# Force the launcher PowerShell process to terminate even if the shortcut host was started with -NoExit.
[Environment]::Exit(0)
