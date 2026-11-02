"""Left navigation sidebar."""
from __future__ import annotations

from typing import Callable, Dict

import customtkinter as ctk

from .. import icons, theme
from ..config import APP_NAME
from ..theme import font

NAV = [("dashboard", "Dashboard", "dashboard"), ("send", "Send Document", "send"), ("inbox", "Inbox", "inbox"),
       ("sent", "Sent Files", "sent"), ("lab", "BB84 Security Lab", "lab"), ("activity", "Activity Log", "activity"),
       ("profile", "Profile", "profile"), ("settings", "Settings", "settings"), ("about", "About", "about")]
_ICON = ("#C9DCEB", "#B7CCDD")
_ICON_ACTIVE = ("#FFFFFF", "#FFFFFF")


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_select: Callable[[str], None], on_logout: Callable[[], None]):
        super().__init__(parent, fg_color=theme.SIDEBAR_BG, corner_radius=0, width=236)
        self.grid_propagate(False)
        self.buttons: Dict[str, ctk.CTkButton] = {}
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 18))
        ctk.CTkLabel(brand, text="", image=icons.logo(38)).pack(side="left")
        col = ctk.CTkFrame(brand, fg_color="transparent")
        col.pack(side="left", padx=10)
        ctk.CTkLabel(col, text=APP_NAME, font=font(21, "bold"), text_color="#FFFFFF", anchor="w").pack(anchor="w")
        ctk.CTkLabel(col, text="Secure medical exchange", font=font(10), text_color=theme.SIDEBAR_TEXT, anchor="w").pack(anchor="w")
        for key, label, icon_name in NAV:
            btn = ctk.CTkButton(self, text="  " + label, anchor="w", height=42, corner_radius=8, font=font(13, "bold"),
                                fg_color="transparent", hover_color=theme.SIDEBAR_HOVER, text_color=theme.SIDEBAR_TEXT,
                                image=icons.icon(icon_name, 19, _ICON), compound="left", command=lambda k=key: on_select(k))
            btn.pack(fill="x", padx=12, pady=2)
            self.buttons[key] = btn
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)
        out = ctk.CTkButton(self, text="  Logout", anchor="w", height=42, corner_radius=8, font=font(13, "bold"),
                            fg_color="transparent", hover_color=theme.SIDEBAR_HOVER, text_color=theme.SIDEBAR_TEXT,
                            image=icons.icon("logout", 19, _ICON), compound="left", command=on_logout)
        out.pack(fill="x", padx=12, pady=(0, 18))

    def select(self, key: str) -> None:
        for k, btn in self.buttons.items():
            icon_name = next(i for kk, _, i in NAV if kk == k)
            active = k == key
            btn.configure(fg_color=theme.SIDEBAR_ACTIVE if active else "transparent",
                          text_color=("#FFFFFF", "#FFFFFF") if active else theme.SIDEBAR_TEXT,
                          image=icons.icon(icon_name, 19, _ICON_ACTIVE if active else _ICON))
