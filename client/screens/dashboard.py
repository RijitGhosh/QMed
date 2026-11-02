"""Dashboard: statistics cards and recent activity."""
from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from .. import theme
from ..components.cards import Badge, Card, PrimaryButton, SecondaryButton, StatCard, PageHeader
from ..components.tables import DataTable, fmt_time
from ..theme import font
from .base import PAD, Screen

CARDS = [("total_sent", "Total Sent", "send", theme.PRIMARY, "Documents sent"),
         ("total_received", "Total Received", "inbox", theme.TEAL, "Documents in your inbox"),
         ("successful_transfers", "Successful Transfers", "check", theme.EMERALD, "Encrypted & delivered"),
         ("security_checks", "Security Checks", "shield", theme.CYAN, "BB84 simulations run"),
         ("threats_detected", "Threats Detected", "warning", theme.AMBER, "QBER above threshold"),
         ("pending_documents", "Pending Documents", "file", theme.PRIMARY, "Waiting for your action")]


def greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


class DashboardScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        self.head = PageHeader(self, "", "")
        self.head.pack(fill="x", **PAD, pady=(22, 10))
        self.role_badge = Badge(self.head.actions, "", "teal")
        self.role_badge.pack(side="right", padx=8)
        PrimaryButton(self.head.actions, "Send Document", lambda: shell.navigate("send"), "send").pack(side="right")
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", **PAD)
        self.cards = {}
        for i, (key, title, icon_name, accent, sub) in enumerate(CARDS):
            c = StatCard(grid, title, icon_name, accent, sub)
            c.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="ew")
            grid.grid_columnconfigure(i % 3, weight=1, uniform="stat")
            self.cards[key] = c
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", **PAD, pady=(14, 4))
        ctk.CTkLabel(row, text="Recent Activity", font=font(17, "bold"), text_color=theme.TEXT).pack(side="left")
        self.server = ctk.CTkLabel(row, text="", font=font(12), text_color=theme.MUTED)
        self.server.pack(side="right")
        self.table = DataTable(self, [
            {"key": "time", "title": "Time", "weight": 2, "min": 150}, {"key": "event", "title": "Event", "weight": 3, "min": 170},
            {"key": "status", "title": "Status", "weight": 1, "min": 100, "kind": "badge"},
            {"key": "doc", "title": "Document", "weight": 2, "min": 130, "kind": "mono"},
            {"key": "desc", "title": "Details", "weight": 4, "min": 220, "max": 48}],
            empty_title="No activity yet", empty_text="Your sign-ins, transfers and security checks will appear here.",
            empty_kind="sent", height=330)
        self.table.pack(fill="x", **PAD, pady=(0, 20))
        app.connection_listeners.append(self._conn)

    def _conn(self, ok: bool) -> None:
        self.server.configure(text=("● Connected to QMed Server  " if ok else "● Disconnected  ") + self.app.api.base_url,
                              text_color=theme.EMERALD if ok else theme.RED)

    def on_show(self) -> None:
        u = self.app.user
        self.head.winfo_children()[0].configure(text=f"{greeting()}, {u['full_name']}")
        self.head.winfo_children()[1].configure(text=f"Signed in as {u['role']} · @{u['username']}") if len(self.head.winfo_children()) > 2 else None
        self.role_badge.update_kind(u["role"], "teal")
        self._conn(bool(self.app.connected))
        self.app.run_async(self.app.api.dashboard, self._loaded)

    def _loaded(self, data) -> None:
        for key, card in self.cards.items():
            card.set_value(data.get(key, 0))
        self.table.set_rows([{"time": fmt_time(e["timestamp"]), "event": e["action"].replace("_", " ").title(),
                              "status": e["status"].title(), "status_kind": theme.STATUS_KIND.get(e["status"], "info"),
                              "doc": e.get("transfer_id") or "–", "desc": e.get("description") or ""}
                             for e in data["recent_activity"]])
