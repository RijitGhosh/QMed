"""Server configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

from common.bb84 import DEFAULT_QBER_THRESHOLD
from common.validation import DEFAULT_ALLOWED_EXTENSIONS, PasswordPolicy

BASE_DIR = Path(__file__).resolve().parent.parent
APP_VERSION = "1.0.0"


def _bool(value: Optional[str], default: bool) -> bool:
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 5000
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    storage_dir: Path = BASE_DIR / "storage"
    log_dir: Path = BASE_DIR / "logs"
    database_url: str = ""
    secret_key: str = ""
    session_hours: int = 8
    max_file_bytes: int = 10 * 1024 * 1024
    allowed_extensions: Tuple[str, ...] = DEFAULT_ALLOWED_EXTENSIONS
    qber_threshold: float = DEFAULT_QBER_THRESHOLD
    password_policy: PasswordPolicy = field(default_factory=PasswordPolicy)
    allow_self_send: bool = False
    testing: bool = False

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.storage_dir, self.log_dir):
            path.mkdir(parents=True, exist_ok=True)

    def resolve_secret(self) -> str:
        """Use QMED_SECRET_KEY, else create/read a persisted random secret."""
        if self.secret_key:
            return self.secret_key
        key_file = self.data_dir / "server_secret.key"
        if key_file.exists():
            return key_file.read_text().strip()
        secret = secrets.token_hex(32)
        key_file.write_text(secret)
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass
        return secret

    def public_config(self) -> dict:
        """Server-controlled values exposed to clients."""
        return {
            "version": APP_VERSION,
            "qber_threshold": self.qber_threshold,
            "max_file_bytes": self.max_file_bytes,
            "allowed_extensions": list(self.allowed_extensions),
            "session_hours": self.session_hours,
            "password_policy": self.password_policy.to_dict(),
            "allow_self_send": self.allow_self_send,
        }


def load_settings(**overrides) -> Settings:
    load_dotenv(BASE_DIR / ".env")
    env = os.environ.get
    s = Settings(
        host=env("QMED_HOST", "0.0.0.0"),
        port=int(env("QMED_PORT", "5000")),
        secret_key=env("QMED_SECRET_KEY", ""),
        session_hours=int(env("QMED_SESSION_HOURS", "8")),
        max_file_bytes=int(float(env("QMED_MAX_FILE_MB", "10")) * 1024 * 1024),
        allowed_extensions=tuple(e.strip().lower().lstrip(".") for e in
                                 env("QMED_ALLOWED_EXTENSIONS", ",".join(DEFAULT_ALLOWED_EXTENSIONS)).split(",") if e.strip()),
        qber_threshold=float(env("QMED_QBER_THRESHOLD", str(DEFAULT_QBER_THRESHOLD))),
        password_policy=PasswordPolicy(
            min_length=int(env("QMED_PASSWORD_MIN_LENGTH", "8")),
            require_symbol=_bool(env("QMED_PASSWORD_REQUIRE_SYMBOL"), False)),
        allow_self_send=_bool(env("QMED_ALLOW_SELF_SEND"), False),
    )
    for key, value in overrides.items():
        setattr(s, key, value)
    if not s.database_url:
        s.database_url = env("QMED_DATABASE_URL") or f"sqlite:///{(s.data_dir / 'qmed.db').as_posix()}"
    return s
