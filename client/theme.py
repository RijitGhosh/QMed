"""QMed visual identity. Colours are (light, dark) tuples; CustomTkinter switches them with the theme.

Palette: medical blue, deep navy, teal, cyan, emerald, white, blue-grey, amber (warning), red (error).
There is intentionally NO purple / violet / magenta anywhere.
"""
from __future__ import annotations

import sys
from typing import Dict, Tuple

import customtkinter as ctk

Pair = Tuple[str, str]

BG: Pair = ("#F1F6FA", "#0A1724")
SURFACE: Pair = ("#FFFFFF", "#10253A")
SURFACE_ALT: Pair = ("#E8F0F6", "#163049")
BORDER: Pair = ("#D0DDE8", "#25425C")
TEXT: Pair = ("#0D2A40", "#E8F1F8")
MUTED: Pair = ("#587185", "#93AABD")
PRIMARY: Pair = ("#0A6CB5", "#1E88D8")
PRIMARY_HOVER: Pair = ("#085490", "#3B9CE8")
TEAL: Pair = ("#0B8F9C", "#22B8C7")
TEAL_HOVER: Pair = ("#077682", "#48CCDA")
CYAN: Pair = ("#0EA5C6", "#3CCBE8")
EMERALD: Pair = ("#0F9D6A", "#2BC48A")
EMERALD_HOVER: Pair = ("#0B7E54", "#4AD6A0")
AMBER: Pair = ("#D98A0B", "#F2B24A")
RED: Pair = ("#C62F2F", "#F06B6B")
RED_HOVER: Pair = ("#A32323", "#F58C8C")
NEUTRAL_BTN: Pair = ("#DCE6EE", "#1D3A54")
NEUTRAL_BTN_HOVER: Pair = ("#C9D8E4", "#28496A")
SIDEBAR_BG: Pair = ("#0C2B47", "#08141F")
SIDEBAR_TEXT: Pair = ("#C9DCEB", "#B7CCDD")
SIDEBAR_ACTIVE: Pair = ("#12507F", "#0F3F63")
SIDEBAR_HOVER: Pair = ("#123B5E", "#0E2A42")
WHITE = "#FFFFFF"

BADGES: Dict[str, Tuple[Pair, Pair]] = {  # (background, text)
    "success": (("#DDF5EA", "#12382B"), ("#0B6B45", "#5FE0A6")),
    "warning": (("#FFF0D6", "#3F2E0E"), ("#8A5300", "#FFC46B")),
    "error": (("#FDE3E3", "#452020"), ("#A31C1C", "#FF8A8A")),
    "pending": (("#E3EBF2", "#1F3448"), ("#41586B", "#A9BDCF")),
    "blocked": (("#F9D0D0", "#5A1A1A"), ("#8B1111", "#FFB3B3")),
    "info": (("#DCEBFA", "#173A5A"), ("#0A5A9C", "#7CC0F5")),
    "teal": (("#D8F3F5", "#0F3A40"), ("#0A6E78", "#6FE3EE")),
}

STATUS_KIND = {"PENDING": "pending", "SECURITY_CHECK_FAILED": "warning", "ENCRYPTED": "info", "SENT": "info",
               "DELIVERED": "teal", "DECRYPTED": "success", "FAILED": "error", "BLOCKED": "blocked",
               "SUCCESS": "success", "FAILURE": "error", "WARNING": "warning", "VERIFIED": "success",
               "UNVERIFIED": "pending", "PASS": "success", "POSSIBLE_EAVESDROPPING": "blocked"}
STATUS_LABEL = {"SECURITY_CHECK_FAILED": "Security Check Failed", "SENT": "Encrypted & Sent",
                "POSSIBLE_EAVESDROPPING": "Possible Eavesdropping"}


def status_label(status: str) -> str:
    return STATUS_LABEL.get(status, status.replace("_", " ").title())


def pick(pair: Pair) -> str:
    """Resolve a colour pair for widgets that do not understand tuples (e.g. raw Canvas)."""
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]


_FAMILY = {"win32": "Segoe UI", "darwin": "Helvetica Neue"}.get(sys.platform, "DejaVu Sans")
_font_cache: Dict[tuple, ctk.CTkFont] = {}


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    key = (size, weight)
    if key not in _font_cache:
        _font_cache[key] = ctk.CTkFont(family=_FAMILY, size=size, weight=weight)
    return _font_cache[key]


def mono(size: int = 11) -> ctk.CTkFont:
    return ctk.CTkFont(family="Consolas" if sys.platform == "win32" else "DejaVu Sans Mono", size=size)
