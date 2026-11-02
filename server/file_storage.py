"""Ciphertext storage using random identifiers (user input never forms a path)."""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from .errors import ApiError

_STORED_NAME_RE = re.compile(r"^[0-9a-f]{32}\.qmed$")


class FileStorage:
    def __init__(self, base_dir: Path):
        self.base = Path(base_dir).resolve() / "transfers"
        self.base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, stored_name: str) -> Path:
        if not _STORED_NAME_RE.match(stored_name or ""):
            raise ApiError(400, "INVALID_FILE_REFERENCE", "Invalid stored file reference.")
        path = (self.base / stored_name).resolve()
        if path.parent != self.base:  # defence in depth against traversal
            raise ApiError(400, "INVALID_FILE_REFERENCE", "Invalid stored file reference.")
        return path

    def save(self, ciphertext: bytes) -> str:
        name = f"{secrets.token_hex(16)}.qmed"
        self._resolve(name).write_bytes(ciphertext)
        return name

    def read(self, stored_name: str) -> bytes:
        path = self._resolve(stored_name)
        if not path.exists():
            raise ApiError(404, "FILE_NOT_FOUND", "The encrypted file is missing on the server.")
        return path.read_bytes()
