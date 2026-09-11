import json
import os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".claude_meter.json")


class Config:
    def __init__(self):
        self.cookies = {}  # dict of name: value
        self.org_id = ""
        self.autostart = True
        self._load()

    @property
    def logged_in(self):
        return "sessionKey" in self.cookies

    def _load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f:
                    d = json.load(f)
                self.cookies = d.get("cookies", {})
                self.org_id = d.get("org_id", "")
                self.autostart = d.get("autostart", True)
            except:
                pass

    def save(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump({
                "cookies": self.cookies,
                "org_id": self.org_id,
                "autostart": self.autostart,
            }, f)
