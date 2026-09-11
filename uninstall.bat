@echo off
title Claude Meter Uninstaller
echo.
echo   Claude Meter Uninstaller
echo   =============================================
echo   This removes the app but KEEPS your settings and log.
echo.
pause

taskkill /f /im pythonw.exe 2>nul
taskkill /f /im python.exe 2>nul
taskkill /f /im ClaudeMeter.exe 2>nul
timeout /t 2 /nobreak >nul

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
