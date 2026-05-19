# Disco Rhythm Analyzer

A small Tkinter desktop app that analyzes an audio file, estimates the primary BPM, and outputs a timestamped map of BPM changes through the track. The UI is disco-themed, bilingual, and designed to be packaged as a Windows release with GitHub Actions.

## Features

- Supports `.mp3`, `.wav`, `.flac`, `.ogg`, `.aac`, and `.m4a`
- Estimates the primary BPM of the track
- Outputs timestamps where the detected BPM changes
- Uses a scrollable results panel for longer tempo maps
- Caps analysis to the first 15 minutes to avoid runaway CPU and memory use
- Rejects files larger than 250 MB
- Runs audio analysis off the Tkinter main thread
- Updates Tkinter only from the GUI thread
- Includes a GitHub Actions workflow that builds a Windows installer and portable zip on version tags

## For Testers

Download `DeadAsDiscoAnalyzer-Setup-vX.X.X.exe` from the latest GitHub Release and run it. You do not need to run PowerShell scripts or build the project yourself.

The portable `RhythmAnalyzer-windows.zip` is also available, but the installer is the easiest option for most testers.

Because the app is not code-signed yet, Windows may still show a SmartScreen warning. A paid code-signing certificate is the proper way to remove most untrusted-publisher warnings.

## Local Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m rhythm_analyzer
```

You can also run the VS Code task named `Run app`.

## Build A Windows App Locally

```powershell
.\scripts\build-windows.ps1
```

The packaged app will be written to `dist\RhythmAnalyzer`.

To build the installer locally, install Inno Setup 6 and run:

```powershell
.\scripts\build-installer.ps1 -AppVersion 1.1.2
```

## GitHub Release Build

1. Push this project to GitHub.
2. Create and push a version tag:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

3. The `Build Release` workflow builds `DeadAsDiscoAnalyzer-Setup-vX.X.X.exe` and `RhythmAnalyzer-windows.zip`, then attaches both to the GitHub Release for that tag.

## App Icon

The project includes `assets/discoball.ico`, which is used for the executable and app window. If it is removed, the build script and app fall back to `assets/icon.ico`.

## Notes

This project intentionally uses conservative resource limits because audio decoders and media files can be expensive or malformed. Keep dependencies current before publishing new releases.
