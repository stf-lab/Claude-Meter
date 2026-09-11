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
; Stop the running tray app (pythonw running claude_meter.py only; other Python programs untouched).
; "{{" is Inno Setup's escape for a literal "{".
Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -in 'python.exe','pythonw.exe') -and ($_.CommandLine -like '*claude_meter.py*') } | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"""; Flags: runhidden waituntilterminated; RunOnceId: "StopApp"
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v ""ClaudeMeter"" /f"; Flags: runhidden; RunOnceId: "RemoveAutostart"

[UninstallDelete]
; Created by engine.bat, not by [Files], so Inno would otherwise leave them behind.
; Settings in %USERPROFILE%\.claude_meter.json are kept on purpose.
Type: filesandordirs; Name: "{localappdata}\ClaudeMeter\app"
Type: filesandordirs; Name: "{localappdata}\ClaudeMeter\python"
Type: files; Name: "{userdesktop}\Claude Meter.lnk"
Type: files; Name: "{userprograms}\Claude Meter.lnk"
Type: dirifempty; Name: "{localappdata}\ClaudeMeter"
