"""
Auth: sessionKey paste + extension auto-connect.
Falls back to PowerShell dialog if tkinter unavailable (embedded Python).
"""

import logging
import threading
import json
import os
import sys
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

log = logging.getLogger(__name__)

AUTH_PORT = 27182
EXTENSION_URL = "https://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe"


class _AuthHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/auth":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                sk = data.get("sk", "")
                if sk and len(sk) > 20:
                    self.server.session_key = sk
                    if self.server.on_key_received:
                        self.server.on_key_received(sk)
                    self.send_response(200)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK")
                    log.info(f"Auth server: received key ({len(sk)} chars)")
                    return
            except Exception as e:
                log.info(f"Auth parse error: {e}")
        self.send_response(400)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


class AuthServer:
    def __init__(self, on_key_callback=None):
        self.on_key_callback = on_key_callback
        self._server = None

    def start(self):
        try:
            self._server = HTTPServer(("127.0.0.1", AUTH_PORT), _AuthHandler)
            self._server.session_key = None
            self._server.on_key_received = self.on_key_callback
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
            log.info(f"Auth server started on port {AUTH_PORT}")
        except OSError as e:
            log.info(f"Auth server port in use: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()


def _verify_key(sk):
    try:
        from curl_cffi import requests as cf
        test = cf.get("https://claude.ai/api/organizations",
                      cookies={"sessionKey": sk}, impersonate="chrome",
                      timeout=10, verify=False)
        return test.status_code == 200
    except Exception as e:
        log.info(f"Verify error: {e}")
        return False


def _login_tkinter(auth_server):
    """Login dialog using tkinter."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    result = {"cookies": None}

    root = tk.Tk()
    root.title("Claude Meter - Connect")
    root.geometry("460x360")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 460) // 2
    y = (root.winfo_screenheight() - 360) // 2
    root.geometry(f"460x360+{x}+{y}")

    ttk.Label(root, text="Connect to Claude", font=("Segoe UI", 12, "bold")).pack(pady=(12, 8))

    ext_frame = ttk.LabelFrame(root, text="Recommended: Install browser extension")
    ext_frame.pack(fill="x", padx=15, pady=(0, 8))
    ttk.Label(ext_frame, text="Install Claude Meter extension for automatic login.\nNo manual steps needed after installing.",
              font=("Segoe UI", 9), foreground="gray").pack(padx=10, pady=(5, 3))

    def open_store():
        webbrowser.open(EXTENSION_URL)
        ext_status.set("After installing, browse claude.ai. This dialog closes automatically.")

    ttk.Button(ext_frame, text="Get extension from Chrome Web Store", command=open_store).pack(pady=(0, 3))

    def open_claude():
        webbrowser.open("https://claude.ai")
        ext_status.set("Waiting for extension to connect...")

    ttk.Button(ext_frame, text="I have the extension - connect now", command=open_claude).pack(pady=(0, 3))
    ext_status = tk.StringVar(value="")
    ttk.Label(ext_frame, textvariable=ext_status, font=("Segoe UI", 8), foreground="blue",
              wraplength=400).pack(pady=(0, 6))

    sep = ttk.Separator(root, orient="horizontal")
    sep.pack(fill="x", padx=15, pady=3)
    ttk.Label(root, text="Or connect manually:", font=("Segoe UI", 9, "bold")).pack(pady=(3, 2))

    steps = ttk.Frame(root)
    steps.pack(padx=25)
    for i, step in enumerate([
        "Press F12 on claude.ai > Application > Cookies",
        "Copy  sessionKey  value and paste below",
    ], 1):
        row = ttk.Frame(steps)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=f"{i}.", font=("Segoe UI", 9, "bold"), width=2).pack(side="left")
        ttk.Label(row, text=step, font=("Segoe UI", 9)).pack(side="left")

    key_frame = ttk.Frame(root)
    key_frame.pack(padx=25, fill="x", pady=(5, 0))
    key_var = tk.StringVar()
    entry = ttk.Entry(key_frame, textvariable=key_var, font=("Consolas", 9))
    entry.pack(fill="x")
    entry.focus_set()

    status_var = tk.StringVar(value="")
    ttk.Label(root, textvariable=status_var, font=("Segoe UI", 8), foreground="gray").pack(pady=(3, 0))

    def on_connect():
        val = key_var.get().strip()
        if not val or len(val) < 10:
            status_var.set("Paste the sessionKey value first")
            return
        status_var.set("Verifying...")
        root.update()
        if _verify_key(val):
            result["cookies"] = {"sessionKey": val}
            root.destroy()
        elif val.startswith("sk-ant-"):
            status_var.set("Key looks valid but API rejected it. Try a fresh one.")
        else:
            status_var.set("Invalid key. Make sure you copy the full value.")

    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=6)
    ttk.Button(btn_frame, text="Connect", command=on_connect, width=14).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", command=lambda: root.destroy(), width=10).pack(side="left", padx=5)

    root.bind("<Return>", lambda e: on_connect())
    root.bind("<Escape>", lambda e: root.destroy())

    def check_auth():
        if auth_server and auth_server._server and auth_server._server.session_key:
            sk = auth_server._server.session_key
            if _verify_key(sk):
                result["cookies"] = {"sessionKey": sk}
                root.destroy()
                return
            else:
                auth_server._server.session_key = None
        if root.winfo_exists():
            root.after(500, check_auth)

    root.after(500, check_auth)
    webbrowser.open("https://claude.ai")
    root.mainloop()
    return result.get("cookies")


def _login_powershell(auth_server):
    """Login dialog using PowerShell (fallback when no tkinter)."""
    webbrowser.open("https://claude.ai")

    ps_script = '''
Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type -AssemblyName System.Windows.Forms

$key = [Microsoft.VisualBasic.Interaction]::InputBox(
    "1. Open claude.ai and log in`n2. Press F12 > Application > Cookies > claude.ai`n3. Copy the sessionKey value`n4. Paste below`n`nOr install the browser extension for automatic login:`nhttps://chromewebstore.google.com/detail/claude-meter/hdoipmanokibeilfnibempaiaeilkpfe",
    "Claude Meter - Connect",
    "")
Write-Output $key
'''
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=300
        )
        key = proc.stdout.strip()
        if key and len(key) > 10 and _verify_key(key):
            return {"sessionKey": key}
    except Exception as e:
        log.info(f"PowerShell login error: {e}")
    return None


def login_and_get_cookies(auth_server=None):
    """Login dialog - tries tkinter first, falls back to PowerShell."""
    try:
        import tkinter
        return _login_tkinter(auth_server)
    except ImportError:
        log.info("tkinter not available, using PowerShell dialog")
        return _login_powershell(auth_server)
