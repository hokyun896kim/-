# tools/verify_windows_adapter.ps1 - V3.5 R9 standard asset: verify 7 Windows adapter rules
# Run by a separate Verification Subagent (self-verification forbidden by factory rule)
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$bat = Get-Content "$ProjectDir\run-once.bat" -Raw -Encoding UTF8
$violations = @()
if ($bat -match "(?m)^\s*echo[^\n]*[가-힯]") { $violations += "R1: Hangul echo detected" }
if ($bat -match "(?:cd /d|set [A-Z_]+=)[^\n]*[가-힯]") { $violations += "R2: Hangul path hardcoded (use pushd %~dp0)" }
if ($bat -match "(?m)^\s*timeout\s") { $violations += "R3: timeout used (replace with ping -n N 127.0.0.1 > nul)" }
if ($bat -notmatch "set\s+PYTHONIOENCODING=utf-8") { $violations += "R4a: PYTHONIOENCODING=utf-8 missing" }
if ($bat -notmatch "set\s+PYTHONUTF8=1") { $violations += "R4b: PYTHONUTF8=1 missing" }
if ($bat -notmatch "chcp\s+65001") { $violations += "R5: chcp 65001 missing" }
$pyFiles = Get-ChildItem "$ProjectDir\*.py" -ErrorAction SilentlyContinue
foreach ($py in $pyFiles) {
    $content = Get-Content $py.FullName -Raw -Encoding UTF8
    if ($content -match "print\(" -and $content -notmatch "sys\.stdout\.reconfigure") {
        $violations += "R6: $($py.Name) has print() but no sys.stdout.reconfigure(utf-8)"
    }
}
if (-not (Test-Path "$ProjectDir\install_shortcut.ps1")) { $violations += "R7: install_shortcut.ps1 missing" }

if ($violations.Count -gt 0) {
    Write-Error "Windows adapter rule violations:"
    $violations | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "OK: all 7 Windows adapter rules pass"
