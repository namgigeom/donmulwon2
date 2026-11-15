$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $Root "start_donmulwon_desktop.ps1"
if (-not (Test-Path $Launcher)) { throw "start_donmulwon_desktop.ps1 파일을 찾을 수 없습니다." }
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "DONMULWON 2.lnk"
$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $Launcher + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "DONMULWON 2 개인 사이트 및 친구 공유 링크 실행"
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,14"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "바탕화면에 DONMULWON 2 바로가기를 만들었습니다." -ForegroundColor Green
