# install_shortcut.ps1 - desktop shortcut installer + pre-check (V3.5 R7/R8 standard asset)
param(
    [string]$ShortcutName = "모닝브리핑",
    [string]$TargetBat    = "run-once.bat",
    [string]$IconResource = "%SystemRoot%\System32\shell32.dll,167",
    [string]$Description  = "매일 아침 주식 모닝브리핑 생성 (morning-brief agent)",
    [switch]$SmokeTest
)

$ProjectDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetPath   = Join-Path $ProjectDir $TargetBat
$Desktop      = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"

if (-not (Test-Path $TargetPath)) {
    Write-Error "Target .bat not found: $TargetPath"
    exit 1
}

# R8 pre-check: Hangul in .bat = cmd cp949 decoding failure
$batBytes   = [System.IO.File]::ReadAllBytes($TargetPath)
$batContent = [System.Text.Encoding]::UTF8.GetString($batBytes)
$hangulPattern = "[가-힯ᄀ-ᇿ㄰-㆏]"
if ($batContent -match $hangulPattern) {
    Write-Error "Hangul detected in $TargetPath (V3.5 R6 rule 1 violation)."
    ($batContent -split "`n") | Where-Object { $_ -match $hangulPattern } | ForEach-Object { Write-Host "  > $_" }
    exit 2
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath       = $TargetPath
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.IconLocation     = $IconResource
$Shortcut.Description      = $Description
$Shortcut.Save()

if (-not (Test-Path $ShortcutPath)) {
    Write-Error "Failed to create shortcut"
    exit 1
}
Write-Host "OK: $ShortcutPath"

if ($SmokeTest) {
    Write-Host "Smoke test: triggering shortcut..."
    $logPath = Join-Path $ProjectDir "history.json"
    $before = if (Test-Path $logPath) { (Get-Item $logPath).LastWriteTime } else { Get-Date 0 }
    Start-Process -FilePath $ShortcutPath -Wait
    Start-Sleep -Milliseconds 500
    $after = if (Test-Path $logPath) { (Get-Item $logPath).LastWriteTime } else { Get-Date 0 }
    if ($after -gt $before) { Write-Host "Smoke test OK: history.json updated" }
    else { Write-Warning "Smoke test inconclusive: verify manually" }
}
