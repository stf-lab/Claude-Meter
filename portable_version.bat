@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Claude Meter - Build Portable

set "VER=1.9.0"

echo.
echo   Build Claude Meter v!VER! - portable single exe (Nuitka)
echo   =============================================
echo   Run this from the "x64 Native Tools Command Prompt for VS 2022"
echo   so the MSVC compiler is on PATH.
echo.

:: --- locate Python ---
set "PYCLI="
where python >nul 2>&1
if !errorlevel! equ 0 for /f "tokens=*" %%p in ('where python') do if not defined PYCLI set "PYCLI=%%p"
if "!PYCLI!"=="" (
    echo   [ERROR] Python not found on PATH. Install Python 3.10+.
    pause
    exit /b 1
)
echo   [OK] Python: !PYCLI!

for %%f in (claude_meter.py browser.py config.py icon.ico) do (
    if not exist "%~dp0%%f" ( echo   [ERROR] Missing: %%f & pause & exit /b 1 )
)

:: --- ensure Nuitka ---
"!PYCLI!" -m nuitka --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   [..] Installing Nuitka...
    "!PYCLI!" -m pip install nuitka --no-input
    if errorlevel 1 ( echo   [ERROR] Could not install Nuitka. & pause & exit /b 1 )
)
echo   [OK] Nuitka ready

if not exist "%~dp0portable" mkdir "%~dp0portable"

echo.
echo   [..] Compiling. First build is slow (several minutes). Please wait.
echo.

"!PYCLI!" -m nuitka ^
  --onefile ^
  --assume-yes-for-downloads ^
  --windows-console-mode=disable ^
  --enable-plugin=tk-inter ^
  --include-package=curl_cffi ^
  --include-package-data=curl_cffi ^
  --include-package-data=certifi ^
  --include-data-dir="%~dp0extension=extension" ^
  --windows-icon-from-ico="%~dp0icon.ico" ^
  --company-name="Stefan Savin" ^
  --product-name="Claude Meter" ^
  --file-version=1.9.0 ^
  --product-version=1.9.0 ^
  --file-description="Claude.ai Pro usage tracker" ^
  --copyright="Copyright (c) 2026 Stefan Savin" ^
  --output-dir="%~dp0build_nuitka" ^
  --output-filename=ClaudeMeter_portable_v!VER!.exe ^
  claude_meter.py

if not exist "%~dp0build_nuitka\ClaudeMeter_portable_v!VER!.exe" (
    echo.
    echo   [ERROR] Build failed. Check the Nuitka output above.
    pause
    exit /b 1
)

copy /y "%~dp0build_nuitka\ClaudeMeter_portable_v!VER!.exe" "%~dp0portable\ClaudeMeter_portable_v!VER!.exe" >nul

echo.
echo   Done: %~dp0portable\ClaudeMeter_portable_v!VER!.exe
echo   Needs no Python and no install. Test on a machine WITHOUT Python.
echo.
pause
exit /b 0
