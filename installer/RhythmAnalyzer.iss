#define AppName "Dead as Disco Analyzer"
#ifndef AppVersion
#define AppVersion "1.3"
#endif
#ifndef RepoDir
#define RepoDir ".."
#endif
#ifndef SourceDir
#define SourceDir "..\dist\RhythmAnalyzer"
#endif
#ifndef OutputDir
#define OutputDir "..\dist"
#endif

[Setup]
AppId={{B5D439BB-4F5B-45C6-9B7C-65155618E918}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Joeb5524
AppPublisherURL=https://github.com/Joeb5524/dead-as-disco-analyser
AppSupportURL=https://github.com/Joeb5524/dead-as-disco-analyser/issues
AppUpdatesURL=https://github.com/Joeb5524/dead-as-disco-analyser/releases
DefaultDirName={localappdata}\Programs\Dead as Disco Analyzer
DefaultGroupName=Dead as Disco Analyzer
DisableProgramGroupPage=yes
LicenseFile={#RepoDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=DeadAsDiscoAnalyzer-Setup-v{#AppVersion}
SetupIconFile={#RepoDir}\assets\discoball.ico
UninstallDisplayIcon={app}\RhythmAnalyzer.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Dead as Disco Analyzer"; Filename: "{app}\RhythmAnalyzer.exe"
Name: "{autodesktop}\Dead as Disco Analyzer"; Filename: "{app}\RhythmAnalyzer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RhythmAnalyzer.exe"; Description: "Launch Dead as Disco Analyzer"; Flags: nowait postinstall skipifsilent
