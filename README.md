# Claude Meter

**Windows system tray app + browser extension showing your Claude.ai Pro usage percentage.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Chrome Web Store](https://img.shields.io/chrome-web-store/v/hdoipmanokibeilfnibempaiaeilkpfe)](https://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe)

<!-- Add screenshots here:
![Tray Icon](screenshots/tray.png)
![Extension](screenshots/extension.png)
![Popup](screenshots/popup.png)
-->

## Features

- Color-coded percentage icon: orange (< 80%), red (>= 80%)
- Hover tooltip: 5-hour and 7-day usage with reset countdown
- Auto-refreshes every 90 seconds
- Browser extension shows usage directly in the toolbar
- Click the extension icon for a detailed popup with progress bar
- Automatic login via browser extension (no manual steps after setup)
- Manual sessionKey paste as fallback
- Starts with Windows automatically
- Works with Chrome, Brave, Edge, and other Chromium browsers

## Download

| Version | Description | Download |
|---------|-------------|----------|
| **Browser extension** | Shows usage in browser toolbar | [Chrome Web Store](https://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe) |
| **Portable exe** | Single file, no install needed | [Latest release](https://github.com/stf-lab/Claude-Meter/releases/latest) |
| **Installer** | Full setup; downloads Python if needed | [Latest release](https://github.com/stf-lab/Claude-Meter/releases/latest) |

## Quick Start

### Browser Extension (easiest)
1. Install from [Chrome Web Store](https://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe)
2. Log in to claude.ai
3. Usage percentage appears on the extension icon

### Windows Tray App
1. Download `ClaudeMeter_portable_vX.Y.Z.exe` from the [latest release](https://github.com/stf-lab/Claude-Meter/releases/latest)
2. Place it in a permanent folder and run it
3. Right-click tray icon > **Log in to Claude**
4. Install the browser extension when prompted (for automatic login)
5. Done. Starts with Windows automatically

### Installed Version
1. Download `ClaudeMeter_Setup_vX.Y.Z.exe` from the [latest release](https://github.com/stf-lab/Claude-Meter/releases/latest)
2. Run the installer (downloads Python automatically if not installed)
3. Right-click tray icon > **Log in to Claude**


## How It Works

- The browser extension reads the `sessionKey` cookie from claude.ai and fetches usage data from the undocumented `/api/organizations/{id}/usage` endpoint
- The tray app uses [curl_cffi](https://github.com/yifeikong/curl_cffi) to impersonate Chrome's TLS fingerprint, bypassing Cloudflare
- The extension sends the sessionKey (and the organization selected in claude.ai) to the tray app via a local HTTP server on `127.0.0.1:27182`; the server only accepts requests from browser extensions
- Session keys persist across restarts, lasting days to weeks


## Building from Source

### Requirements
- Windows 10/11
- Python 3.10+ ([python.org](https://python.org), check "Add to PATH")
- Chrome, Brave, or Edge browser

### Build the Installer
Requires [Inno Setup 7](https://jrsoftware.org/isinfo.php):
```
installed_version.bat
```
Creates `install\ClaudeMeter_Setup_vX.Y.Z.exe`

### Build the Portable Exe
Requires a C compiler (MSVC recommended):
```
portable_version.bat
```
Creates `portable\ClaudeMeter_portable_vX.Y.Z.exe`

Best run from the "x64 Native Tools Command Prompt for VS 2022" for MSVC. Nuitka downloads its own compiler if MSVC is not found.

### Publishing a Release
The built exes are not committed to git. After building both:
1. Create a GitHub Release tagged `vX.Y.Z`
2. Attach `install\ClaudeMeter_Setup_vX.Y.Z.exe` and `portable\ClaudeMeter_portable_vX.Y.Z.exe`


## Project Structure

```
claude_meter.py      Main tray app
browser.py           Login / auth server (extension + manual fallback)
config.py            Settings load/save
make_launcher.py     Generates the VBS launcher (used during install)
make_icon.py         Regenerates icon.ico
icon.ico             App icon
extension/           Browser extension source
  background.js      Polls usage, updates icon, sends key to tray app
  popup.html/js      Extension popup with progress bar
  manifest.json      Extension manifest (MV3)
  icons/             Static extension icons (16, 48, 128 px)
engine.bat           Install engine (called by installer, not run directly)
installed_version.bat  Build the installer Setup.exe
portable_version.bat   Build the portable single exe
uninstall.bat        Remove the app
installer.iss        Inno Setup script
```


## Privacy

- The app and extension only communicate with claude.ai (the installer also downloads Python and packages from python.org and PyPI when needed)
- Session key stored locally (`~/.claude_meter.json`)
- Local auth server listens only on 127.0.0.1 (not accessible from the network)
- No data collected, no analytics, no tracking


## Windows SmartScreen / Antivirus

Unsigned executables trigger SmartScreen on first run: click "More info" > "Run anyway". This is normal for unsigned software. An application for free open-source code signing through [SignPath](https://signpath.io) has been submitted.


## License

[MIT](LICENSE)


## Author

**Stefan Savin** - [github.com/stf-lab](https://github.com/stf-lab)
