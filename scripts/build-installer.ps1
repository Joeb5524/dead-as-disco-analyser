param(
    [string]$AppVersion = "1.1.3"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppDir = (Resolve-Path (Join-Path $Root "dist\RhythmAnalyzer")).Path
$OutputDir = (Resolve-Path (Join-Path $Root "dist")).Path

$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$InnoCompiler = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $InnoCompiler) {
    throw "Inno Setup 6 compiler not found. Install it with: choco install innosetup -y"
}

& $InnoCompiler `
    (Join-Path $Root "installer\RhythmAnalyzer.iss") `
    "/DAppVersion=$AppVersion" `
    "/DRepoDir=$Root" `
    "/DSourceDir=$AppDir" `
    "/DOutputDir=$OutputDir"
