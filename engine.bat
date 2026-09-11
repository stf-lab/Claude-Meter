@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: =====================================================================
::  engine.bat - the Claude Meter install engine (internal).
::  You normally do NOT run this directly. It is called by:
::    - installed_version.bat (to stage the app before compiling Setup.exe)
::    - the shipped Setup.exe, as "engine.bat /S", on each user machine
::  Pass /S for silent (no pause, no auto-launch).
:: =====================================================================

set "VER=1.9.0"
set "SILENT=0"
if /i "%~1"=="/S" set "SILENT=1"

title Claude Meter v!VER! Installer
echo.
echo   Claude Meter v!VER! - setting up
echo   =============================================
echo.

for %%f in (config.py browser.py claude_meter.py) do (
    if not exist "%~dp0%%f" (
        echo   [ERROR] Missing: %%f
        if "!SILENT!"=="0" pause
        exit /b 1
    )
)

set "DEST=%LOCALAPPDATA%\ClaudeMeter"
set "APPDIR=!DEST!\app"
if not exist "!APPDIR!" mkdir "!APPDIR!"

:: --- system Python? ---
set "PYTHON="
where pythonw >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%p in ('where pythonw') do if not defined PYTHON set "PYTHON=%%p"
    for /f "tokens=*" %%p in ('where python')  do if not defined PYTHONCLI set "PYTHONCLI=%%p"
    echo   [OK] Found system Python: !PYTHON!
    set "PYTHONW=!PYTHON!"
    goto :install_deps
)

:: --- no system Python: fetch embedded ---
echo   [..] Python not found. Downloading embedded Python...
set "PYVER=3.12.8"
set "PYZIP=python-!PYVER!-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/!PYVER!/!PYZIP!"
set "PYDIR=!DEST!\python"

if exist "!PYDIR!\pythonw.exe" (
    echo   [OK] Embedded Python already present
    set "APPPATH=!DEST!\app"
    for %%f in ("!PYDIR!\python*._pth") do (
        findstr /c:"!APPPATH!" "%%f" >nul 2>&1
        if errorlevel 1 ( echo.>> "%%f" & echo !APPPATH!>> "%%f" )
    )
    goto :set_embedded
)

if not exist "!PYDIR!" mkdir "!PYDIR!"
echo   [..] Downloading Python !PYVER!...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PYURL!' -OutFile '!DEST!\!PYZIP!' -UseBasicParsing"
if not exist "!DEST!\!PYZIP!" (
    echo   [ERROR] Download failed. Install Python 3.10+ from https://python.org
    if "!SILENT!"=="0" pause
    exit /b 1
)
echo   [..] Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '!DEST!\!PYZIP!' -DestinationPath '!PYDIR!' -Force"
del "!DEST!\!PYZIP!" >nul 2>&1

for %%f in ("!PYDIR!\python*._pth") do (
    powershell -NoProfile -Command "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)

echo   [..] Installing pip...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '!DEST!\get-pip.py' -UseBasicParsing"
"!PYDIR!\python.exe" "!DEST!\get-pip.py" --no-warn-script-location
del "!DEST!\get-pip.py" >nul 2>&1

set "APPPATH=!DEST!\app"
for %%f in ("!PYDIR!\python*._pth") do (
    findstr /c:"!APPPATH!" "%%f" >nul 2>&1
    if errorlevel 1 ( echo.>> "%%f" & echo !APPPATH!>> "%%f" )
)

:set_embedded
set "PYTHONCLI=!PYDIR!\python.exe"
set "PYTHONW=!PYDIR!\pythonw.exe"

:install_deps
echo   [..] Installing packages (may take a few minutes)...
"!PYTHONCLI!" -m pip install --upgrade pip --no-input 2>nul
"!PYTHONCLI!" -m pip install pystray Pillow requests curl_cffi --no-input
echo   [OK] Packages installed

for %%f in (config.py browser.py claude_meter.py) do copy /y "%~dp0%%f" "!APPDIR!\" >nul
if exist "%~dp0icon.ico"         copy /y "%~dp0icon.ico" "!APPDIR!\" >nul
if exist "%~dp0README.md"        copy /y "%~dp0README.md" "!APPDIR!\" >nul
if exist "%~dp0make_launcher.py" copy /y "%~dp0make_launcher.py" "!APPDIR!\" >nul
if exist "%~dp0extension"        xcopy /y /e /i "%~dp0extension" "!APPDIR!\extension\" >nul
echo   [OK] Files copied

"!PYTHONCLI!" "!APPDIR!\make_launcher.py"

echo   [..] Creating shortcuts...
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Claude Meter.lnk'); $s.TargetPath='!APPDIR!\ClaudeMeter.vbs'; $s.IconLocation='!APPDIR!\icon.ico'; $s.Description='Claude.ai Pro usage tracker'; $s.Save()" >nul 2>&1
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('!SM!\Claude Meter.lnk'); $s.TargetPath='!APPDIR!\ClaudeMeter.vbs'; $s.IconLocation='!APPDIR!\icon.ico'; $s.Description='Claude.ai Pro usage tracker'; $s.Save()" >nul 2>&1
echo   [OK] Shortcuts created

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ClaudeMeter" /t REG_SZ /d "wscript.exe \"!APPDIR!\ClaudeMeter.vbs\"" /f >nul 2>&1
echo   [OK] Added to Windows startup

echo.
echo   Setup complete.
echo   For automatic login, install the browser extension:
echo   https://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe
echo.

if "!SILENT!"=="0" (
    start "" wscript.exe "!APPDIR!\ClaudeMeter.vbs"
    echo   [OK] Launched.
    pause
)
exit /b 0
