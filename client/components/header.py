"""Top bar: page title, server status, current user/role, theme toggle, logout."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .. import icons, theme
from ..theme import font
from .cards import Badge, Tooltip


class Header(ctk.CTkFrame):
    def __init__(self, parent, app, on_logout: Callable[[], None]):
        super().__init__(parent, fg_color=theme.SURFACE, corner_radius=0, height=64, border_width=0)
        self.app = app
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.title = ctk.CTkLabel(self, text="", font=font(16, "bold"), text_color=theme.TEXT, anchor="w")
        self.title.grid(row=0, column=0, padx=24, sticky="w")
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, padx=16, sticky="e")
        self.status_dot = ctk.CTkLabel(right, text="", width=18, image=icons.fixed_icon("dot", 12, "#8FA3B3"))
        self.status_dot.pack(side="left")
        self.status_text = ctk.CTkLabel(right, text="Checking…", font=font(12), text_color=theme.MUTED)
        self.status_text.pack(side="left", padx=(0, 18))
        who = ctk.CTkFrame(right, fg_color="transparent")
        who.pack(side="left", padx=(0, 14))
        self.name = ctk.CTkLabel(who, text="", font=font(13, "bold"), text_color=theme.TEXT, anchor="e")
        self.name.pack(anchor="e")
        self.role = Badge(who, "Role", "teal")
        self.role.pack(anchor="e", pady=(2, 0))
        self.theme_btn = ctk.CTkButton(right, text="", width=40, height=40, corner_radius=20, fg_color=theme.NEUTRAL_BTN,
                                       hover_color=theme.NEUTRAL_BTN_HOVER, command=app.toggle_theme)
        self.theme_btn.pack(side="left", padx=4)
        Tooltip(self.theme_btn, "Toggle light / dark theme")
        out = ctk.CTkButton(right, text="", width=40, height=40, corner_radius=20, fg_color=theme.NEUTRAL_BTN,
                            hover_color=theme.NEUTRAL_BTN_HOVER, image=icons.icon("logout", 18, theme.TEXT), command=on_logout)
        out.pack(side="left", padx=4)
        Tooltip(out, "Sign out")
        self.refresh_theme_icon()
        self.set_user(app.user)

    def set_title(self, text: str) -> None:
        self.title.configure(text=text)

    def set_user(self, user) -> None:
        if user:
            self.name.configure(text=user["full_name"])
            self.role.update_kind(user["role"], "teal")

    def refresh_theme_icon(self) -> None:
        dark = self.app.settings.get("theme") == "dark"
        self.theme_btn.configure(image=icons.icon("moon" if dark else "sun", 20, ("#D98A0B", "#9FD3F5")))

    def set_connection(self, connected: bool) -> None:
        self.status_dot.configure(image=icons.fixed_icon("dot", 12, "#0F9D6A" if connected else "#C62F2F"))
        self.status_text.configure(text="Connected to QMed Server" if connected else "Disconnected")
