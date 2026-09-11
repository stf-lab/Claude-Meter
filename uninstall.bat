@echo off
title Claude Meter Uninstaller
echo.
echo   Claude Meter Uninstaller
echo   =============================================
echo   This removes the app but KEEPS your settings and log.
echo.
pause

:: Stop only Claude Meter: the portable exe, or python/pythonw running claude_meter.py.
:: Other Python programs are left alone.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -like 'ClaudeMeter_portable*.exe') -or (($_.Name -in 'python.exe','pythonw.exe') -and ($_.CommandLine -like '*claude_meter.py*')) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

:: Installed version: run the Inno Setup uninstaller so Windows "Apps" no longer lists it
if exist "%LOCALAPPDATA%\ClaudeMeter\setup\unins000.exe" (
    "%LOCALAPPDATA%\ClaudeMeter\setup\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    timeout /t 3 /nobreak >nul
    echo   [OK] Ran installer's uninstaller
)

if exist "%LOCALAPPDATA%\ClaudeMeter" (
    rmdir /s /q "%LOCALAPPDATA%\ClaudeMeter" 2>nul
    echo   [OK] Removed app folder
) else (
    echo   [--] App folder not found
)

:: user config and logs are intentionally left in place so a later
:: reinstall keeps your saved session. To wipe them manually:
::   del "%USERPROFILE%\.claude_meter.json"
::   del "%USERPROFILE%\.claude_meter.log"
::   del "%USERPROFILE%\claude_meter_diagnostics.txt"

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ClaudeMeter" /f 2>nul
echo   [OK] Removed startup entry

if exist "%USERPROFILE%\Desktop\Claude Meter.lnk" del /f "%USERPROFILE%\Desktop\Claude Meter.lnk"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Claude Meter.lnk" del /f "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Claude Meter.lnk"
echo   [OK] Removed shortcuts

echo.
echo   Uninstall complete.
echo.
pause
