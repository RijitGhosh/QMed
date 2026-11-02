"""Shared inbox / sent-files table with search, filters, sorting and refresh."""
from __future__ import annotations

from typing import Any, Dict, List

import customtkinter as ctk

from common.validation import ROLES, human_size
from .. import icons, theme
from ..components.cards import PageHeader, SecondaryButton
from ..components.tables import DataTable, fmt_time
from ..theme import font
from .base import PAD, Screen
from .transfer_dialogs import TransferDetails

STATUSES = ["All statuses", "PENDING", "SECURITY_CHECK_FAILED", "ENCRYPTED", "SENT", "DELIVERED", "DECRYPTED", "FAILED", "BLOCKED"]


class TransferListScreen(Screen):
    title, subtitle, direction = "", "", "inbox"
    empty_title, empty_text, empty_kind = "", "", "inbox"

    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        self.data: List[Dict[str, Any]] = []
        self.newest_first = True
        head = PageHeader(self, self.title, self.subtitle)
        head.pack(fill="x", **PAD, pady=(22, 10))
        SecondaryButton(head.actions, "Refresh", self.load, "refresh").pack()
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", **PAD, pady=(0, 8))
        self.search = ctk.CTkEntry(bar, placeholder_text="Search file name or username…", width=300, height=36,
                                   fg_color=theme.SURFACE, border_color=theme.BORDER, text_color=theme.TEXT)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self._apply())
        self.status = ctk.CTkOptionMenu(bar, values=[theme.status_label(s) if s != "All statuses" else s for s in STATUSES],
                                        command=lambda _v: self._apply(), width=180, height=36, fg_color=theme.SURFACE_ALT,
                                        button_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)
        self.status.pack(side="left", padx=8)
        self.role = ctk.CTkOptionMenu(bar, values=["All roles", *ROLES], command=lambda _v: self._apply(), width=130, height=36,
                                      fg_color=theme.SURFACE_ALT, button_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)
        self.role.pack(side="left")
        self.sort_btn = SecondaryButton(bar, "Newest first", self._toggle_sort, width=130)
        self.sort_btn.pack(side="left", padx=8)
        self.count = ctk.CTkLabel(bar, text="", font=font(12), text_color=theme.MUTED)
        self.count.pack(side="right")
        self.table = DataTable(self, self.columns(), on_row_click=lambda r: self.details(r["_t"]),
                               empty_title=self.empty_title, empty_text=self.empty_text, empty_kind=self.empty_kind, height=430)
        self.table.pack(fill="x", **PAD, pady=(0, 20))

    # subclass hooks -------------------------------------------------------
    def columns(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def fetch(self):
        raise NotImplementedError

    def row(self, t: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def counterpart(self, t):
        return t["sender"] if self.direction == "inbox" else t["recipient"]

    def details(self, t) -> None:
        TransferDetails(self.app, t)

    # ----------------------------------------------------------------------
    def on_show(self) -> None:
        self.load()

    def load(self) -> None:
        self.app.run_async(self.fetch, self._loaded)

    def _loaded(self, data) -> None:
        self.data = data
        self._apply()

    def _toggle_sort(self) -> None:
        self.newest_first = not self.newest_first
        self.sort_btn.configure(text="Newest first" if self.newest_first else "Oldest first")
        self._apply()

    def _apply(self) -> None:
        q, st, role = self.search.get().strip().lower(), self.status.get(), self.role.get()
        rows = []
        for t in sorted(self.data, key=lambda x: x["created_at"], reverse=self.newest_first):
            who = self.counterpart(t)
            if q and q not in t["original_filename"].lower() and q not in who["username"].lower() and q not in who["full_name"].lower():
                continue
            if st != "All statuses" and theme.status_label(t["status"]) != st:
                continue
            if role != "All roles" and who["role"] != role:
                continue
            rows.append({**self.row(t), "_t": t})
        self.count.configure(text=f"{len(rows)} of {len(self.data)} documents")
        self.table.set_rows(rows)

    @staticmethod
    def security_cell(t):
        if t["qber"] is None:
            return "–", "pending"
        good = t["bb84_status"] == "PASSED"
        return f"QBER {t['qber'] * 100:.1f}% " + ("✓" if good else "✗"), "success" if good else "blocked"
