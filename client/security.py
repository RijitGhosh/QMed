"""Client-side validation helpers and the in-memory key vault (cleared on logout)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from common import crypto
from common.validation import file_extension, human_size


class KeyVault:
    """Holds the unlocked private key only in memory for the signed-in user."""

    def __init__(self) -> None:
        self._private: Optional[bytes] = None

    def unlock(self, blob: dict, password: str) -> None:
        self._private = crypto.unprotect_private_key(blob, password)

    @property
    def private_key(self) -> bytes:
        if self._private is None:
            raise crypto.CryptoError("Your encryption key is locked. Please sign in again.")
        return self._private

    def clear(self) -> None:
        self._private = None


def validate_local_file(path: str, allowed: Tuple[str, ...], max_bytes: int) -> Optional[str]:
    """Return an error message, or None if the file may be sent."""
    p = Path(path)
    if not p.is_file():
        return "The selected file could not be found."
    if file_extension(p.name) not in allowed:
        return "Unsupported file type. Allowed: " + ", ".join(allowed) + "."
    size = p.stat().st_size
    if size == 0:
        return "The selected file is empty."
    if size > max_bytes:
        return f"File is too large ({human_size(size)}). Limit: {human_size(max_bytes)}."
    return None


def unique_path(folder: str, filename: str) -> Path:
    """Destination path that never overwrites an existing file and never escapes `folder`."""
    name = os.path.basename(filename.replace("\\", "/")) or "document"
    target = Path(folder) / name
    stem, suffix, n = target.stem, target.suffix, 1
    while target.exists():
        target = Path(folder) / f"{stem} ({n}){suffix}"
        n += 1
    return target
