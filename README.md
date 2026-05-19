# Disco Rhythm Analyzer

A small Tkinter desktop app that analyzes an audio file, estimates the primary BPM, and outputs a timestamped map of BPM changes through the track. The UI is disco-themed, bilingual, and designed to be packaged as a Windows release with GitHub Actions.

## Features

- Supports `.mp3`, `.wav`, `.flac`, `.ogg`, `.aac`, and `.m4a`
- Estimates the primary BPM of the track
- Outputs timestamps where the detected BPM changes
- Copies game-ready JSON after analysis, including tempo sections, beat offsets, a stable ID/seed, file hash, and source file path
- Can export an analyzed track into an imported songs package with `Meta.JSON` and `audio.ogg`
- Uses a scrollable results panel for longer tempo maps
- Caps analysis to the first 15 minutes to avoid runaway CPU and memory use
- Rejects files larger than 250 MB
- Runs audio analysis off the Tkinter main thread
- Updates Tkinter only from the GUI thread
- Includes a GitHub Actions workflow that builds a Windows installer and portable zip on version tags

## For Testers

Download `DeadAsDiscoAnalyzer-Setup-vX.X.X.exe` from the latest GitHub Release and run it. You do not need to run PowerShell scripts or build the project yourself.

The portable `RhythmAnalyzer-windows.zip` is also available, but the installer is the easiest option for most testers.

Because the app is not code-signed yet, Windows may still show a SmartScreen warning.

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
.\scripts\build-installer.ps1 -AppVersion 1.3
```

## Game JSON Export

After choosing a track, click `COPY JSON` to copy a schema-ready JSON payload to the clipboard. The app can generate `version`, `uniqueId`, `seed`, `songName`, `tempo`, `customTempoSections`, `beatOffset`, `startSongOffset`, `endSongOffset`, `uEAssetName`, `originalAudioFileHash`, and `originalAudioFilePath`.

Fields that require human metadata, such as `performedBy` and `writtenBy`, are included as empty arrays so they can be filled in before importing into the game. Tempo changes and offsets are inferred from audio analysis, so they should be treated as a strong starting point rather than hand-authored chart data.

This JSON output goes in C:\Users\<you>\AppData\Local\Pagoda\Saved\ImportedSongs\songname

## Notes

This project intentionally uses conservative resource limits because audio decoders and media files can be expensive or malformed. Keep dependencies current before publishing new releases.
