"""Modal dialogs and native file pickers."""
from __future__ import annotations

from tkinter import filedialog
from typing import Callable, Optional, Sequence, Tuple

import customtkinter as ctk

from .. import icons, theme
from ..theme import font
from .cards import DangerButton, PrimaryButton, SecondaryButton


class Modal(ctk.CTkToplevel):
    def __init__(self, app, title: str, width: int = 520, height: int = 320):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(fg_color=theme.BG)
        x = app.winfo_rootx() + max(0, (app.winfo_width() - width) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(width, min(height, 240))
        self.transient(app)
        self.after(120, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set(); self.focus_set()
        except Exception:
            pass


def message_dialog(app, kind: str, title: str, text: str) -> None:
    icon_name, accent = {"success": ("check", theme.EMERALD), "warning": ("warning", theme.AMBER),
                         "error": ("error", theme.RED)}.get(kind, ("about", theme.PRIMARY))
    dlg = Modal(app, title, 480, 230)
    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack(fill="both", expand=True, padx=24, pady=(24, 8))
    ctk.CTkLabel(row, text="", image=icons.icon(icon_name, 34, accent)).pack(side="left", anchor="n", padx=(0, 14))
    box = ctk.CTkFrame(row, fg_color="transparent")
    box.pack(side="left", fill="both", expand=True)
    ctk.CTkLabel(box, text=title, font=font(17, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
    ctk.CTkLabel(box, text=text, font=font(13), text_color=theme.MUTED, anchor="w", justify="left", wraplength=340).pack(fill="x", pady=(6, 0))
    PrimaryButton(dlg, "OK", dlg.destroy, width=100).pack(pady=(0, 20))


def confirm_dialog(app, title: str, text: str, on_confirm: Callable, confirm_text: str = "Confirm", danger: bool = False) -> None:
    dlg = Modal(app, title, 460, 220)
    ctk.CTkLabel(dlg, text=title, font=font(17, "bold"), text_color=theme.TEXT).pack(pady=(24, 4), padx=24, anchor="w")
    ctk.CTkLabel(dlg, text=text, font=font(13), text_color=theme.MUTED, wraplength=400, justify="left").pack(padx=24, anchor="w")
    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack(side="bottom", pady=20)
    SecondaryButton(row, "Cancel", dlg.destroy, width=100).pack(side="left", padx=6)
    (DangerButton if danger else PrimaryButton)(row, confirm_text, lambda: (dlg.destroy(), on_confirm()), width=120).pack(side="left", padx=6)


def choose_file(title: str, extensions: Sequence[str], initial: str = "") -> str:
    patterns = " ".join(f"*.{e}" for e in extensions)
    return filedialog.askopenfilename(title=title, initialdir=initial or None,
                                      filetypes=[("Medical documents", patterns), ("All files", "*.*")])


def choose_directory(title: str, initial: str = "") -> str:
    return filedialog.askdirectory(title=title, initialdir=initial or None, mustexist=True)
