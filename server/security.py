"""Password hashing (scrypt, random salt) and login throttling."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

_N, _R, _P = 2 ** 14, 8, 1


def hash_password(password: str) -> Tuple[str, str]:
    """Return (encoded_hash, salt_hex) using scrypt with a fresh 16-byte salt."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32, maxmem=64 * 1024 * 1024)
    return f"scrypt${_N}${_R}${_P}${digest.hex()}", salt.hex()


def verify_password(password: str, encoded: str, salt_hex: str) -> bool:
    try:
        _, n, r, p, digest_hex = encoded.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r),
                                p=int(p), dklen=32, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


class LoginThrottle:
    """In-memory limiter: max `limit` failed logins per `window` seconds per key."""

    def __init__(self, limit: int = 8, window: int = 300):
        self.limit, self.window = limit, window
        self._fails: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> Deque[float]:
        q, now = self._fails[key], time.monotonic()
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.limit

    def record_failure(self, key: str) -> None:
        self._prune(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)
