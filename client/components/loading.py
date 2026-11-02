"""Loading indicator with status text, and a helper to disable buttons while busy."""
from __future__ import annotations

from typing import Iterable

import customtkinter as ctk

from .. import theme
from ..theme import font


class LoadingBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.label = ctk.CTkLabel(self, text="", font=font(12), text_color=theme.MUTED, anchor="w")
        self.label.pack(fill="x")
        self.bar = ctk.CTkProgressBar(self, mode="indeterminate", height=6, progress_color=theme.TEAL, fg_color=theme.SURFACE_ALT)
        self._running = False

    def start(self, text: str) -> None:
        self.label.configure(text=text)
        if not self._running:
            self.bar.pack(fill="x", pady=(4, 0))
            self.bar.start()
            self._running = True

    def stop(self, text: str = "") -> None:
        if self._running:
            self.bar.stop()
            self.bar.pack_forget()
            self._running = False
        self.label.configure(text=text)


def set_busy(widgets: Iterable, busy: bool) -> None:
    for w in widgets:
        try:
            w.configure(state="disabled" if busy else "normal")
        except Exception:
            pass
