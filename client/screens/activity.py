"""Activity log (audit trail of the signed-in user)."""
from __future__ import annotations

import customtkinter as ctk

from .. import theme
from ..components.cards import PageHeader, SecondaryButton
from ..components.tables import DataTable, fmt_time
from .base import PAD, Screen


class ActivityScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        self.events = []
        head = PageHeader(self, "Activity Log", "Security audit trail. Passwords, keys and document contents are never logged.")
        head.pack(fill="x", **PAD, pady=(22, 10))
        SecondaryButton(head.actions, "Refresh", self.on_show, "refresh").pack()
        self.search = ctk.CTkEntry(self, placeholder_text="Filter by action, status or transfer ID…", width=340, height=36,
                                   fg_color=theme.SURFACE, border_color=theme.BORDER, text_color=theme.TEXT)
        self.search.pack(anchor="w", **PAD, pady=(0, 8))
        self.search.bind("<KeyRelease>", lambda _e: self._render())
        self.table = DataTable(self, [
            {"key": "time", "title": "Timestamp", "weight": 2, "min": 150}, {"key": "user", "title": "User", "weight": 1, "min": 90},
            {"key": "action", "title": "Action", "weight": 3, "min": 190, "kind": "mono", "max": 26},
            {"key": "status", "title": "Status", "weight": 1, "min": 100, "kind": "badge"},
            {"key": "transfer", "title": "Transfer ID", "weight": 2, "min": 120, "kind": "mono"},
            {"key": "ip", "title": "IP", "weight": 1, "min": 100},
            {"key": "desc", "title": "Description", "weight": 4, "min": 200, "max": 44}],
            empty_title="No activity recorded", empty_text="Actions you perform will be listed here.", empty_kind="sent", height=470)
        self.table.pack(fill="x", **PAD, pady=(0, 20))

    def on_show(self) -> None:
        self.app.run_async(self.app.api.activity, self._loaded)

    def _loaded(self, events) -> None:
        self.events = events
        self._render()

    def _render(self) -> None:
        q = self.search.get().strip().lower()
        rows = [{"time": fmt_time(e["timestamp"]), "user": e["user"], "action": e["action"], "status": e["status"].title(),
                 "status_kind": theme.STATUS_KIND.get(e["status"], "info"), "transfer": e.get("transfer_id") or "–",
                 "ip": e.get("source_ip") or "–", "desc": e.get("description") or ""}
                for e in self.events if not q or q in (e["action"] + e["status"] + (e.get("transfer_id") or "") + e["user"]).lower()]
        self.table.set_rows(rows)
