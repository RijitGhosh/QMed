"""Local (per-computer) client settings stored in ~/.qmed/client_settings.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "QMed"
APP_TAGLINE = "Quantum-Secure Medical Data Sharing System"
APP_VERSION = "1.0.0"
SETTINGS_DIR = Path.home() / ".qmed"
SETTINGS_FILE = SETTINGS_DIR / "client_settings.json"

DEFAULTS = {
    "server_url": os.environ.get("QMED_SERVER_URL", "http://127.0.0.1:5000"),
    "theme": "light",
    "bb84_bits": 512,
    "qber_threshold": 0.11,
    "last_save_dir": "",
}
HEALTH_CHECK_SECONDS = 20


class LocalSettings:
    def __init__(self, path: Path = SETTINGS_FILE):
        self.path, self.data = path, dict(DEFAULTS)
        try:
            self.data.update(json.loads(path.read_text()))
        except (OSError, ValueError):
            pass

    def get(self, key: str) -> Any:
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, **values: Any) -> None:
        self.data.update(values)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2))
        except OSError:
            pass

    def clear(self) -> None:
        self.data = dict(DEFAULTS)
        try:
            self.path.unlink()
        except OSError:
            pass
