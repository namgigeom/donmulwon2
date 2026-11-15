$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $Root "start_donmulwon_desktop.ps1"
$PngIcon = Join-Path $Root "donmulwon_raccoon.png"
$IcoIcon = Join-Path $Root "donmulwon_raccoon.ico"

if (-not (Test-Path $Launcher)) { throw "start_donmulwon_desktop.ps1 파일을 찾을 수 없습니다." }
if (-not (Test-Path $PngIcon)) {
    throw "너구리 아이콘 파일이 없습니다. donmulwon_raccoon.png를 프로젝트 폴더에 넣은 뒤 다시 실행하세요."
}

Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap($PngIcon)
try {
    $iconHandle = $bitmap.GetHicon()
    try {
        $icon = [System.Drawing.Icon]::FromHandle($iconHandle)
        $stream = [System.IO.File]::Create($IcoIcon)
        try { $icon.Save($stream) } finally { $stream.Dispose() }
    } finally {
        $icon.Dispose()
        Add-Type -TypeDefinition '[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool DestroyIcon(System.IntPtr hIcon);' -Name NativeIcon -Namespace Win32 -ErrorAction SilentlyContinue
        [Win32.NativeIcon]::DestroyIcon($iconHandle) | Out-Null
    }
} finally {
    $bitmap.Dispose()
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "돈물원2.lnk"
$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $Launcher + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "돈물원2 개인 사이트 및 친구 공유 링크 실행"
$Shortcut.IconLocation = "$IcoIcon,0"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "돈물원2 너구리 아이콘 바로가기를 업데이트했습니다." -ForegroundColor Green
Write-Host "아이콘 파일: $IcoIcon"
