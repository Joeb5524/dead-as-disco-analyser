$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

$IconPath = Join-Path $Root "assets\discoball.ico"
if (-not (Test-Path $IconPath)) {
    $IconPath = Join-Path $Root "assets\icon.ico"
}
$Arguments = @(
    "--noconfirm",
    "--clean",
    "--name", "RhythmAnalyzer",
    "--windowed",
    "--collect-binaries", "imageio_ffmpeg",
    "--collect-data", "imageio_ffmpeg",
    "--exclude-module", "librosa.display",
    "--exclude-module", "librosa.decompose",
    "--exclude-module", "librosa.segment",
    "--exclude-module", "matplotlib",
    "--exclude-module", "pandas",
    "--exclude-module", "sklearn",
    "--exclude-module", "PIL",
    "--exclude-module", "openpyxl",
    "--exclude-module", "lxml",
    "src\rhythm_analyzer\app.py"
)

if (Test-Path $IconPath) {
    $Arguments = @("--icon", $IconPath, "--add-data", "$IconPath;assets") + $Arguments
}

python -m PyInstaller @Arguments
