"""Authenticated application shell: sidebar + header + swappable screens."""
from __future__ import annotations

from typing import Dict

import customtkinter as ctk

from . import theme
from .components.dialogs import confirm_dialog
from .components.header import Header
from .components.sidebar import NAV, Sidebar

TITLES = {k: label for k, label, _ in NAV}


class Shell(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = Sidebar(self, self.navigate, self.confirm_logout)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        right = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self.header = Header(right, app, self.confirm_logout)
        self.header.grid(row=0, column=0, sticky="ew")
        self.content = ctk.CTkFrame(right, fg_color="transparent", corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.screens: Dict[str, ctk.CTkFrame] = {}
        self.current = ""
        app.connection_listeners.append(self._on_connection)
        if app.connected is not None:
            self.header.set_connection(app.connected)

    def _on_connection(self, ok: bool) -> None:
        self.header.set_connection(ok)

    def confirm_logout(self) -> None:
        confirm_dialog(self.app, "Sign out", "Sign out of QMed? Your encryption key will be cleared from memory.",
                       self.app.logout, "Sign out")

    def _build(self, key: str):
        from .screens.about import AboutScreen
        from .screens.activity import ActivityScreen
        from .screens.bb84_lab import LabScreen
        from .screens.dashboard import DashboardScreen
        from .screens.inbox import InboxScreen
        from .screens.profile import ProfileScreen
        from .screens.send_document import SendScreen
        from .screens.sent_files import SentScreen
        from .screens.settings import SettingsScreen
        return {"dashboard": DashboardScreen, "send": SendScreen, "inbox": InboxScreen, "sent": SentScreen,
                "lab": LabScreen, "activity": ActivityScreen, "profile": ProfileScreen, "settings": SettingsScreen,
                "about": AboutScreen}[key](self.content, self.app, self)

    def navigate(self, key: str) -> None:
        if self.current and self.current in self.screens:
            self.screens[self.current].pack_forget()
        if key not in self.screens:
            self.screens[key] = self._build(key)
        self.current = key
        self.sidebar.select(key)
        self.header.set_title(TITLES[key])
        self.screens[key].pack(fill="both", expand=True)
        self.screens[key].on_show()

    def destroy(self) -> None:
        if self._on_connection in self.app.connection_listeners:
            self.app.connection_listeners.remove(self._on_connection)
        super().destroy()
