$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $Root "start_donmulwon_desktop.ps1"
$PngIcon = Join-Path $Root "donmulwon_raccoon.png"
$IcoIcon = Join-Path $Root "donmulwon_raccoon_v2.ico"

if (-not (Test-Path $Launcher)) { throw "start_donmulwon_desktop.ps1 파일을 찾을 수 없습니다." }
if (-not (Test-Path $PngIcon)) {
    throw "너구리 아이콘 파일이 없습니다. donmulwon_raccoon.png를 프로젝트 폴더에 넣은 뒤 다시 실행하세요."
}

Add-Type -AssemblyName System.Drawing
$source = [System.Drawing.Bitmap]::FromFile($PngIcon)
$target = New-Object System.Drawing.Bitmap(256, 256, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
try {
    $graphics = [System.Drawing.Graphics]::FromImage($target)
    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($source, 0, 0, 256, 256)
    } finally {
        $graphics.Dispose()
    }

    $pngStream = New-Object System.IO.MemoryStream
    try {
        $target.Save($pngStream, [System.Drawing.Imaging.ImageFormat]::Png)
        $pngBytes = $pngStream.ToArray()
    } finally {
        $pngStream.Dispose()
    }
} finally {
    $target.Dispose()
    $source.Dispose()
}

# Build a valid 256x256 PNG-compressed ICO file (no unmanaged HICON handles).
$icoStream = [System.IO.File]::Open($IcoIcon, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
$writer = New-Object System.IO.BinaryWriter($icoStream)
try {
    $writer.Write([UInt16]0)              # Reserved
    $writer.Write([UInt16]1)              # ICO type
    $writer.Write([UInt16]1)              # Image count
    $writer.Write([Byte]0)                # Width: 0 means 256
    $writer.Write([Byte]0)                # Height: 0 means 256
    $writer.Write([Byte]0)                # Color count
    $writer.Write([Byte]0)                # Reserved
    $writer.Write([UInt16]1)              # Color planes
    $writer.Write([UInt16]32)             # Bits per pixel
    $writer.Write([UInt32]$pngBytes.Length)
    $writer.Write([UInt32]22)             # Image data offset
    $writer.Write($pngBytes)
} finally {
    $writer.Dispose()
    $icoStream.Dispose()
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutName = ([char]0xB3C8).ToString() + ([char]0xBB3C) + ([char]0xC6D0) + "2.lnk"
$ShortcutPath = Join-Path $Desktop $ShortcutName
$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $Launcher + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "DONMULWON2 personal site and friend sharing launcher"
$Shortcut.IconLocation = "$IcoIcon,0"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "DONMULWON2 desktop shortcut updated." -ForegroundColor Green
Write-Host "아이콘 파일: $IcoIcon"
