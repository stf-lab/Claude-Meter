; Claude Meter - Inno Setup Installer
; Bundles source files, runs engine.bat to set up Python + deps on the user machine

#define MyAppName "Claude Meter"
#define MyAppVersion "1.9.0"
#define MyAppPublisher "Stefan Savin"
#define MyAppURL "https://github.com/stf-lab/claude-meter"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppCopyright=Copyright (c) 2026 Stefan Savin
DefaultDirName={localappdata}\ClaudeMeter\setup
DefaultGroupName={#MyAppName}
OutputBaseFilename=ClaudeMeter_Setup_v{#MyAppVersion}
OutputDir={#SourcePath}\install
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
DisableDirPage=yes
SetupIconFile={#SourcePath}\icon.ico

[Files]
; Bundle all source files from the zip folder
Source: "{#SourcePath}\claude_meter.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\browser.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\make_launcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\engine.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs

[Run]
; Run engine.bat; /S = silent
Filename: "{cmd}"; Parameters: "/c ""{app}\engine.bat"" /S"; WorkingDir: "{app}"; Flags: waituntilterminated; StatusMsg: "Setting up Python and dependencies..."
; Launch the app
Filename: "wscript.exe"; Parameters: """{localappdata}\ClaudeMeter\app\ClaudeMeter.vbs"""; Flags: nowait postinstall skipifsilent; Description: "Launch {#MyAppName}"

[UninstallRun]
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v ""ClaudeMeter"" /f"; Flags: runhidden
