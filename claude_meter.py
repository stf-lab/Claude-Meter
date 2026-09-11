"""
Claude Meter v1.9.0 - System tray app showing Claude.ai Pro usage.
Uses curl_cffi to bypass Cloudflare. Session key persists across restarts.
"""

import sys
import os

# Ensure local modules (browser.py, config.py) can be found
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import threading
import time
import json
import logging
import webbrowser
from datetime import datetime, timezone

import pystray
from PIL import Image, ImageDraw, ImageFont
from curl_cffi import requests as cf_requests

from browser import login_and_get_cookies, AuthServer
from config import Config

logging.basicConfig(
    filename=os.path.join(os.path.expanduser("~"), ".claude_meter.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

ICON_SIZE = 64
POLL_INTERVAL = 90


class ClaudeMeter:
    def __init__(self):
        self.config = Config()
        self.pct = -1
        self.status_text = "Claude Meter"
        self.icon = None
        self.running = True
        self._polling_started = False
        self._org_id = self.config.org_id
        self._session_expired_notified = False
        self._fail_count = 0

        # Auth server - receives keys from browser extension
        self.auth_server = AuthServer(on_key_callback=self._on_auto_key)
        self.auth_server.start()

    def _on_auto_key(self, sk):
        """Called when extension sends a fresh sessionKey."""
        log.info(f"Auto-key received ({len(sk)} chars)")
        try:
            test = cf_requests.get("https://claude.ai/api/organizations",
                                   cookies={"sessionKey": sk}, impersonate="chrome",
                                   timeout=10, verify=False)
            if test.status_code == 200:
                self.config.cookies = {"sessionKey": sk}
                self.config.org_id = ""
                self._org_id = ""
                self._fail_count = 0
                self._session_expired_notified = False
                self.config.save()
                log.info("Auto-key verified and saved")
                self._start_polling()
                threading.Thread(target=self._poll_once, daemon=True).start()
        except Exception as e:
            log.info(f"Auto-key verify error: {e}")

    def _make_image(self):
        img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if self.pct < 0:
            bg, fg = (100, 100, 100), (255, 255, 255)
            text = "?"
        else:
            p = self.pct
            if p < 80:
                bg, fg = (217, 119, 87), (255, 255, 255)
            else:
                bg, fg = (232, 78, 78), (255, 255, 255)
            text = str(p)
        draw.ellipse([1, 1, ICON_SIZE - 1, ICON_SIZE - 1], fill=bg)
        if len(text) == 1: fsize = 44
        elif len(text) == 2: fsize = 36
        else: fsize = 28
        try:
            font = ImageFont.truetype("arialbd.ttf", fsize)
        except OSError:
            try: font = ImageFont.truetype("arial.ttf", fsize)
            except OSError: font = ImageFont.load_default()
        cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
        draw.text((cx, cy), text, fill=fg, font=font, anchor="mm")
        return img

    def _set_status(self, text):
        self.status_text = text[:127]

    def _refresh(self):
        if self.icon:
            self.icon.icon = self._make_image()
            self.icon.title = self.status_text

    def _notify(self, title, msg):
        if self.icon:
            try: self.icon.notify(msg, title)
            except: pass

    def _api_get(self, path):
        try:
            r = cf_requests.get(
                f"https://claude.ai/api/{path}",
                cookies=self.config.cookies,
                impersonate="chrome",
                verify=False,
                timeout=15,
            )
            return {"status": r.status_code, "body": r.text}
        except Exception as e:
            log.info(f"API error: {e}")
            return None

    def _ensure_org_id(self):
        if self._org_id:
            return self._org_id
        resp = self._api_get("organizations")
        if resp and resp["status"] == 200:
            try:
                orgs = json.loads(resp["body"])
                if orgs and isinstance(orgs, list):
                    self._org_id = orgs[0].get("uuid", "")
                    self.config.org_id = self._org_id
                    self.config.save()
                    return self._org_id
            except: pass
        if resp:
            log.info(f"/organizations: {resp['status']} {resp['body'][:200]}")
        return ""

    def _parse_usage(self, data):
        if not isinstance(data, dict): return None
        five = data.get("five_hour")
        seven = data.get("seven_day")
        if five and isinstance(five, dict) and "utilization" in five:
            pct5 = int(float(five["utilization"]))
            detail = f"5h: {pct5}%"
            if seven and isinstance(seven, dict) and "utilization" in seven:
                pct7 = int(float(seven["utilization"]))
                detail += f", 7d: {pct7}%"
            resets_at = five.get("resets_at")
            if resets_at:
                try:
                    reset_time = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    secs = int((reset_time - now).total_seconds())
                    if secs > 0:
                        h, m = secs // 3600, (secs % 3600) // 60
                        detail += f" | Resets in {h}h{m:02d}m" if h > 0 else f" | Resets in {m}m"
                    else:
                        detail += " | Resetting..."
                except: pass
            return {"pct": pct5, "detail": detail}
        return None

    def _poll_once(self):
        try:
            if not self.config.logged_in:
                self.pct = -1
                self._set_status("Right-click > Log in")
                self._refresh()
                return

            org_id = self._ensure_org_id()
            if not org_id:
                self._fail_count += 1
                self.pct = -1
                if self._fail_count <= 2:
                    self._set_status("Reconnecting...")
                else:
                    self._set_status("Session expired - right-click > Log in")
                    if not self._session_expired_notified:
                        self._session_expired_notified = True
                        self._notify("Claude Meter", "Session expired. Right-click > Log in to reconnect.")
                self._refresh()
                return

            self._session_expired_notified = False
            self._fail_count = 0

            resp = self._api_get(f"organizations/{org_id}/usage")
            if resp and resp["status"] == 200:
                try:
                    data = json.loads(resp["body"])
                    parsed = self._parse_usage(data)
                    if parsed:
                        self.pct = parsed["pct"]
                        if parsed.get("detail"):
                            self._set_status(f"Claude use: ({parsed['detail']})")
                        else:
                            self._set_status(f"Claude use: {self.pct}%")
                        self._refresh()
                        return
                except: pass
            elif resp and resp["status"] == 429:
                self.pct = 100
                self._set_status("Claude: 100% used (rate limited)")
                self._refresh()
                return
            elif resp and resp["status"] in (401, 403):
                self._fail_count += 1
                self._org_id = ""
                if self._fail_count <= 2:
                    self.pct = -1
                    self._set_status("Reconnecting...")
                    self._refresh()
                    return
                self.pct = -1
                self._set_status("Session expired - right-click > Log in")
                if not self._session_expired_notified:
                    self._session_expired_notified = True
                    self._notify("Claude Meter", "Session expired. Right-click > Log in to reconnect.")
                self._refresh()
                return

            resp2 = self._api_get(f"organizations/{org_id}/chat_conversations")
            if resp2 and resp2["status"] == 200:
                self.pct = 0
                self._set_status("Claude: connected (usage data N/A)")
            elif resp2 and resp2["status"] == 429:
                self.pct = 100
                self._set_status("Claude: 100% (rate limited)")
            else:
                self.pct = -1
                st = resp2["status"] if resp2 else "timeout"
                self._set_status(f"API: {st}")
        except Exception as e:
            log.exception("Poll error")
            self.pct = -1
            self._set_status(f"Error: {e}")
        self._refresh()

    def _poll_loop(self):
        while self.running:
            self._poll_once()
            for _ in range(POLL_INTERVAL):
                if not self.running: return
                time.sleep(1)

    def _start_polling(self):
        if not self._polling_started:
            self._polling_started = True
            threading.Thread(target=self._poll_loop, daemon=True).start()

    def _on_refresh(self, *a):
        threading.Thread(target=self._poll_once, daemon=True).start()

    def _on_login(self, *a):
        threading.Thread(target=self._do_login, daemon=True).start()

    def _do_login(self):
        log.info("=== LOGIN START ===")
        self._set_status("Connecting...")
        self._refresh()

        # Try extension first: open claude.ai and wait for key
        if self.auth_server and self.auth_server._server:
            self.auth_server._server.session_key = None
            webbrowser.open("https://claude.ai")
            log.info("Opened claude.ai, waiting for extension...")
            for i in range(15):
                if self.auth_server._server.session_key:
                    sk = self.auth_server._server.session_key
                    self.auth_server._server.session_key = None
                    from browser import _verify_key
                    if _verify_key(sk):
                        self.config.cookies = {"sessionKey": sk}
                        self.config.org_id = ""
                        self._org_id = ""
                        self._fail_count = 0
                        self._session_expired_notified = False
                        self.config.save()
                        log.info("Login via extension succeeded")
                        self._start_polling()
                        self._poll_once()
                        log.info("=== LOGIN END ===")
                        return
                time.sleep(1)
            log.info("Extension didn't respond, showing dialog")

        # Fall back to dialog
        cookies = login_and_get_cookies(auth_server=self.auth_server)
        if cookies:
            self.config.cookies = cookies
            self.config.org_id = ""
            self._org_id = ""
            self._fail_count = 0
            self._session_expired_notified = False
            self.config.save()
            log.info(f"Login: saved {len(cookies)} cookies")
            self._start_polling()
            self._poll_once()
        else:
            self._set_status("Login cancelled")
            self._refresh()
        log.info("=== LOGIN END ===")

    def _on_logout(self, *a):
        self.config.cookies = {}
        self.config.org_id = ""
        self._org_id = ""
        self.config.save()
        self.pct = -1
        self._polling_started = False
        self._set_status("Logged out")
        self._refresh()

    def _on_diagnostics(self, *a):
        threading.Thread(target=self._run_diag, daemon=True).start()

    def _run_diag(self):
        lines = ["=== Claude Meter v1.9.0 Diagnostics ===\n"]
        lines.append(f"Cookies: {len(self.config.cookies)} cookies, sessionKey={'yes' if self.config.logged_in else 'no'}")
        lines.append(f"Org ID: {self._org_id or 'NOT SET'}")
        lines.append(f"Status: {self.status_text}")
        lines.append("\n--- API test ---\n")
        resp = self._api_get("organizations")
        if resp:
            lines.append(f"GET /organizations: {resp['status']}")
            lines.append(f"Body: {resp['body'][:500]}")
            if resp["status"] == 200:
                try:
                    orgs = json.loads(resp["body"])
                    if orgs:
                        oid = orgs[0].get("uuid", "")
                        lines.append(f"\nOrg: {oid}")
                        for ep in ["usage", "chat_conversations"]:
                            r2 = self._api_get(f"organizations/{oid}/{ep}")
                            if r2:
                                lines.append(f"\nGET /{ep}: {r2['status']}")
                                lines.append(f"  {r2['body'][:300]}")
                except Exception as e:
                    lines.append(f"Parse error: {e}")
        else:
            lines.append("No response")
        lines.append("\n\n--- Recent log ---\n")
        logpath = os.path.join(os.path.expanduser("~"), ".claude_meter.log")
        try:
            with open(logpath) as f:
                for line in f.readlines()[-25:]:
                    lines.append(line.rstrip())
        except: pass
        diag_path = os.path.join(os.path.expanduser("~"), "claude_meter_diagnostics.txt")
        with open(diag_path, "w") as f:
            f.write("\n".join(lines))
        os.startfile(diag_path)

    def _on_about(self, *a):
        import subprocess
        text = (
            "Claude Meter v1.9.0`n`n"
            "System tray app showing your`n"
            "Claude.ai Pro usage percentage.`n`n"
            "Author: Stefan Savin`n"
            "License: MIT`n"
            "GitHub: github.com/stf-lab/claude-meter`n`n"
            "© 2026 Stefan Savin"
        )
        subprocess.Popen([
            "powershell", "-NoProfile", "-Command",
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f'[System.Windows.Forms.MessageBox]::Show("{text}", "About Claude Meter", '
            f"[System.Windows.Forms.MessageBoxButtons]::OK, "
            f"[System.Windows.Forms.MessageBoxIcon]::Information)"
        ], creationflags=0x08000000)

    def _on_github(self, *a):
        webbrowser.open("https://github.com/stf-lab/claude-meter")

    def _on_autostart(self, *a):
        self.config.autostart = not self.config.autostart
        self.config.save()
        self._apply_autostart()

    def _apply_autostart(self):
        """Set or remove Windows startup registry entry."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if self.config.autostart:
                # Nuitka onefile: use the exe itself
                if getattr(sys, 'frozen', False) or '__compiled__' in globals():
                    exe = sys.executable
                    winreg.SetValueEx(key, "ClaudeMeter", 0, winreg.REG_SZ,
                                      f'"{exe}"')
                else:
                    # Source mode: use VBS launcher if available
                    app_dir = os.path.dirname(os.path.abspath(__file__))
                    vbs = os.path.join(app_dir, "ClaudeMeter.vbs")
                    if os.path.exists(vbs):
                        winreg.SetValueEx(key, "ClaudeMeter", 0, winreg.REG_SZ,
                                          f'wscript.exe "{vbs}"')
                    else:
                        # Fallback: run python directly
                        script = os.path.join(app_dir, "claude_meter.py")
                        winreg.SetValueEx(key, "ClaudeMeter", 0, winreg.REG_SZ,
                                          f'pythonw "{script}"')
            else:
                try: winreg.DeleteValue(key, "ClaudeMeter")
                except: pass
            winreg.CloseKey(key)
        except: pass

    def _on_quit(self, *a):
        self.running = False
        self.auth_server.stop()
        if self.icon:
            self.icon.stop()

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Refresh", self._on_refresh, default=True),
            pystray.MenuItem("Log in to Claude...", self._on_login,
                             visible=lambda i: not self.config.logged_in),
            pystray.MenuItem("Switch account...", self._on_login,
                             visible=lambda i: self.config.logged_in),
            pystray.MenuItem("Log out", self._on_logout,
                             visible=lambda i: self.config.logged_in),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Diagnostics...", self._on_diagnostics),
            pystray.MenuItem("Start with Windows", self._on_autostart,
                             checked=lambda i: self.config.autostart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("About...", self._on_about),
            pystray.MenuItem("GitHub", self._on_github),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )
        self.icon = pystray.Icon("claude_meter", self._make_image(), self.status_text, menu)

        # Apply autostart on first run
        if self.config.autostart:
            self._apply_autostart()

        if self.config.logged_in:
            self._start_polling()
        else:
            self._set_status("Right-click > Log in to Claude")

        self.icon.run()


if __name__ == "__main__":
    ClaudeMeter().run()
