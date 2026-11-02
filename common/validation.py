"""Input validation shared by client (fast feedback) and server (authoritative)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

ROLES: Tuple[str, ...] = ("Doctor", "Patient", "Other")
DEFAULT_ALLOWED_EXTENSIONS: Tuple[str, ...] = ("txt", "pdf", "docx", "csv", "png", "jpg", "jpeg")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
HEX_RE = re.compile(r"^[0-9a-f]+$")
TRANSFER_REF_RE = re.compile(r"^QMED-\d{4}-\d{4,9}$")

MAX_NAME_LEN = 80
MAX_MESSAGE_LEN = 500
MAX_FILENAME_LEN = 200


@dataclass(frozen=True)
class PasswordPolicy:
    """Configurable password strength requirements."""

    min_length: int = 8
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_symbol: bool = False

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PasswordPolicy":
        if not data:
            return cls()
        allowed = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**allowed)


def check_password(password: str, policy: PasswordPolicy) -> List[str]:
    """Return a list of human-readable problems (empty list = acceptable)."""
    problems: List[str] = []
    if len(password) < policy.min_length:
        problems.append(f"Password must contain at least {policy.min_length} characters.")
    if len(password) > 128:
        problems.append("Password must be at most 128 characters.")
    if policy.require_upper and not re.search(r"[A-Z]", password):
        problems.append("Password must contain an uppercase letter.")
    if policy.require_lower and not re.search(r"[a-z]", password):
        problems.append("Password must contain a lowercase letter.")
    if policy.require_digit and not re.search(r"\d", password):
        problems.append("Password must contain a digit.")
    if policy.require_symbol and not re.search(r"[^A-Za-z0-9]", password):
        problems.append("Password must contain a symbol.")
    return problems


def password_strength(password: str) -> Tuple[int, str]:
    """Return (score 0-4, label) for the strength indicator."""
    if not password:
        return 0, "Empty"
    score = 0
    score += len(password) >= 8
    score += len(password) >= 12
    score += bool(re.search(r"[a-z]", password) and re.search(r"[A-Z]", password))
    score += bool(re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password))
    labels = ["Very weak", "Weak", "Fair", "Good", "Strong"]
    return score, labels[score]


def validate_username(username: str) -> Optional[str]:
    if not username:
        return "Username is required."
    if not USERNAME_RE.match(username):
        return "Username must be 3-32 characters: letters, digits, dot, dash or underscore."
    return None


def validate_email(email: str) -> Optional[str]:
    if not email:
        return "Email is required."
    if len(email) > 254 or not EMAIL_RE.match(email):
        return "Enter a valid email address."
    return None


def validate_role(role: str) -> Optional[str]:
    return None if role in ROLES else "Role must be Doctor, Patient or Other."


def clean_text(value: object, max_len: int) -> str:
    """Strip control characters and surrounding whitespace, then truncate."""
    text = "" if value is None else str(value)
    text = "".join(ch for ch in text if ch in "\n\t " or unicodedata.category(ch)[0] != "C")
    return text.strip()[:max_len]


def safe_filename(name: str) -> str:
    """Return a display-safe base filename (never used as a filesystem path)."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = clean_text(name, MAX_FILENAME_LEN).strip(". ")
    return name


def file_extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_hex(value: object, length: Optional[int] = None) -> bool:
    if not isinstance(value, str) or not value or not HEX_RE.match(value):
        return False
    return length is None or len(value) == length


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"
