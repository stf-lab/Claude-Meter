@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Claude Meter - Build Installer

set "VER=1.9.0"

echo.
echo   Build Claude Meter v!VER! Setup.exe
echo   =============================================
echo.

:: --- stage the app (calls the shared install engine, silently) ---
call "%~dp0engine.bat" /S
if not exist "%LOCALAPPDATA%\ClaudeMeter\app\claude_meter.py" (
    echo   [ERROR] Staging failed - app not set up.
    pause
    exit /b 1
)
echo   [OK] App staged

if not exist "%~dp0icon.ico" (
    echo   [ERROR] icon.ico not found.
    pause
    exit /b 1
)

:: --- find Inno Setup ---
set "ISCC="
for %%p in (
    "%PROGRAMFILES%\Inno Setup 7\ISCC.exe"
    "%PROGRAMFILES(X86)%\Inno Setup 7\ISCC.exe"
    "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
    "%PROGRAMFILES%\Inno Setup 6\ISCC.exe"
    "%PROGRAMFILES(X86)%\Inno Setup 6\ISCC.exe"
) do (
    if exist %%~p set "ISCC=%%~p"
)
if "!ISCC!"=="" (
    echo   [ERROR] Inno Setup not found. https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)
echo   [OK] Found Inno Setup

echo   [..] Compiling installer...
"!ISCC!" "%~dp0installer.iss"

if exist "%~dp0install\ClaudeMeter_Setup_v!VER!.exe" (
    echo.
    echo   Done: %~dp0install\ClaudeMeter_Setup_v!VER!.exe
) else (
    echo.
    echo   [ERROR] Compilation failed - Setup.exe not produced.
)
echo.
pause
exit /b 0
