"""Stacked toast notifications (success / warning / error / info)."""
from __future__ import annotations

from typing import List

import customtkinter as ctk

from .. import icons, theme
from ..theme import font

_KIND = {"success": ("check", theme.EMERALD), "warning": ("warning", theme.AMBER),
         "error": ("error", theme.RED), "info": ("about", theme.PRIMARY)}


class Toaster:
    def __init__(self, root):
        self.root, self.items = root, []  # type: ignore[var-annotated]

    def show(self, kind: str, message: str, ms: int = 5000) -> None:
        icon_name, accent = _KIND.get(kind, _KIND["info"])
        frame = ctk.CTkFrame(self.root, fg_color=theme.SURFACE, border_color=accent, border_width=2, corner_radius=10)
        ctk.CTkLabel(frame, text="", image=icons.icon(icon_name, 20, accent)).pack(side="left", padx=(12, 6), pady=12)
        ctk.CTkLabel(frame, text=message, font=font(12), text_color=theme.TEXT, wraplength=330, justify="left").pack(
            side="left", padx=(0, 14), pady=10)
        close = lambda f=frame: self._dismiss(f)
        frame.bind("<Button-1>", lambda _e: close())
        self.items.append(frame)
        self._layout()
        frame.after(ms, close)

    def _dismiss(self, frame) -> None:
        if frame in self.items:
            self.items.remove(frame)
            frame.destroy()
            self._layout()

    def _layout(self) -> None:
        y = 78
        for f in self.items:
            f.place(relx=1.0, x=-20, y=y, anchor="ne")
            f.lift()
            f.update_idletasks()
            y += f.winfo_reqheight() + 8
