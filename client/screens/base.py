"""Base classes shared by all screens."""
from __future__ import annotations

import customtkinter as ctk

from .. import icons, theme
from ..config import APP_NAME, APP_TAGLINE
from ..theme import font
from ..components.cards import Tooltip


class Screen(ctk.CTkScrollableFrame):
    """Scrollable page inside the authenticated shell."""

    def __init__(self, parent, app, shell):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.app, self.shell = app, shell

    def on_show(self) -> None:  # called every time the page is opened
        pass


PAD = {"padx": 28}


class PublicTopBar(ctk.CTkFrame):
    """Logo (left) and theme toggle (right) for pre-login screens."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        ctk.CTkLabel(self, text=f" {APP_NAME}", image=icons.logo(36), compound="left", font=font(22, "bold"),
                     text_color=theme.TEXT).pack(side="left", padx=24, pady=16)
        self.btn = ctk.CTkButton(self, text="", width=40, height=40, corner_radius=20, fg_color=theme.NEUTRAL_BTN,
                                 hover_color=theme.NEUTRAL_BTN_HOVER, command=app.toggle_theme)
        self.btn.pack(side="right", padx=24)
        Tooltip(self.btn, "Toggle light / dark theme")
        self.refresh()

    def refresh(self) -> None:
        dark = self.app.settings.get("theme") == "dark"
        self.btn.configure(image=icons.icon("moon" if dark else "sun", 20, ("#D98A0B", "#9FD3F5")))


class PublicScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.topbar = PublicTopBar(self, app)
        self.topbar.pack(fill="x")

    def refresh_theme_icon(self) -> None:
        self.topbar.refresh()
