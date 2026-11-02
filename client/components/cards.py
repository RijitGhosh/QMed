"""Reusable UI building blocks: buttons, cards, badges, form fields, tooltips."""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Iterable, Optional, Tuple

import customtkinter as ctk

from .. import icons, theme
from ..theme import font


class _Button(ctk.CTkButton):
    def __init__(self, parent, text: str = "", command: Optional[Callable] = None, icon_name: Optional[str] = None, *,
                 fg, hover, text_color, icon_color, width: int = 0, height: int = 36, **kw):
        img = icons.icon(icon_name, 18, icon_color) if icon_name else None
        super().__init__(parent, text=text, command=command, image=img, compound="left", fg_color=fg,
                         hover_color=hover, text_color=text_color, height=height, corner_radius=8,
                         font=font(13, "bold"), **({"width": width} if width else {}), **kw)


class PrimaryButton(_Button):
    def __init__(self, parent, text="", command=None, icon_name=None, **kw):
        super().__init__(parent, text, command, icon_name, fg=theme.PRIMARY, hover=theme.PRIMARY_HOVER,
                         text_color=theme.WHITE, icon_color=(theme.WHITE, theme.WHITE), **kw)


class SecondaryButton(_Button):
    def __init__(self, parent, text="", command=None, icon_name=None, **kw):
        super().__init__(parent, text, command, icon_name, fg=theme.NEUTRAL_BTN, hover=theme.NEUTRAL_BTN_HOVER,
                         text_color=theme.TEXT, icon_color=theme.TEXT, **kw)


class SuccessButton(_Button):
    def __init__(self, parent, text="", command=None, icon_name=None, **kw):
        super().__init__(parent, text, command, icon_name, fg=theme.EMERALD, hover=theme.EMERALD_HOVER,
                         text_color=theme.WHITE, icon_color=(theme.WHITE, theme.WHITE), **kw)


class DangerButton(_Button):
    def __init__(self, parent, text="", command=None, icon_name=None, **kw):
        super().__init__(parent, text, command, icon_name, fg=theme.RED, hover=theme.RED_HOVER,
                         text_color=theme.WHITE, icon_color=(theme.WHITE, theme.WHITE), **kw)


class Card(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        kw.setdefault("fg_color", theme.SURFACE)
        super().__init__(parent, corner_radius=12, border_width=1, border_color=theme.BORDER, **kw)


class Badge(ctk.CTkLabel):
    """Coloured status pill: success / warning / error / pending / blocked / info / teal."""

    def __init__(self, parent, text: str, kind: str = "info"):
        bg, fg = theme.BADGES.get(kind, theme.BADGES["info"])
        super().__init__(parent, text=f"  {text}  ", fg_color=bg, text_color=fg, corner_radius=11, height=22,
                         font=font(11, "bold"))

    def update_kind(self, text: str, kind: str) -> None:
        bg, fg = theme.BADGES.get(kind, theme.BADGES["info"])
        self.configure(text=f"  {text}  ", fg_color=bg, text_color=fg)


def status_badge(parent, status: str) -> Badge:
    return Badge(parent, theme.status_label(status), theme.STATUS_KIND.get(status, "info"))


class StatCard(Card):
    def __init__(self, parent, title: str, icon_name: str, accent: theme.Pair, subtitle: str = ""):
        super().__init__(parent)
        self.grid_columnconfigure(1, weight=1)
        chip = ctk.CTkFrame(self, fg_color=accent, corner_radius=10, width=44, height=44)
        chip.grid(row=0, column=0, rowspan=3, padx=(16, 12), pady=16)
        chip.grid_propagate(False)
        ctk.CTkLabel(chip, text="", image=icons.icon(icon_name, 22, (theme.WHITE, theme.WHITE))).place(relx=.5, rely=.5, anchor="center")
        ctk.CTkLabel(self, text=title, font=font(12), text_color=theme.MUTED, anchor="w").grid(row=0, column=1, sticky="w", pady=(14, 0))
        self.value = ctk.CTkLabel(self, text="–", font=font(26, "bold"), text_color=theme.TEXT, anchor="w")
        self.value.grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(self, text=subtitle, font=font(11), text_color=theme.MUTED, anchor="w").grid(row=2, column=1, sticky="w", pady=(0, 12))

    def set_value(self, value) -> None:
        self.value.configure(text=str(value))


class PageHeader(ctk.CTkFrame):
    def __init__(self, parent, title: str, subtitle: str = ""):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, font=font(24, "bold"), text_color=theme.TEXT, anchor="w").grid(row=0, column=0, sticky="w")
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=font(13), text_color=theme.MUTED, anchor="w", justify="left",
                         wraplength=820).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.actions = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self.actions.grid(row=0, column=1, rowspan=2, sticky="e")


class Field(ctk.CTkFrame):
    """Label + entry + inline error line; optional password visibility toggle."""

    def __init__(self, parent, label: str, placeholder: str = "", secret: bool = False, width: int = 0):
        super().__init__(parent, fg_color="transparent")
        self.secret, self._shown = secret, False
        ctk.CTkLabel(self, text=label, font=font(12, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        self.entry = ctk.CTkEntry(row, placeholder_text=placeholder, height=38, show="•" if secret else "",
                                  fg_color=theme.SURFACE, border_color=theme.BORDER, text_color=theme.TEXT,
                                  placeholder_text_color=theme.MUTED, font=font(13), **({"width": width} if width else {}))
        self.entry.pack(side="left", fill="x", expand=True)
        if secret:
            self.eye = ctk.CTkButton(row, text="", width=38, height=38, image=icons.icon("eye", 18, theme.MUTED),
                                     fg_color=theme.NEUTRAL_BTN, hover_color=theme.NEUTRAL_BTN_HOVER, command=self.toggle)
            self.eye.pack(side="left", padx=(6, 0))
            Tooltip(self.eye, "Show / hide password")
        self.error = ctk.CTkLabel(self, text="", height=16, font=font(11), text_color=theme.RED, anchor="w", justify="left", wraplength=420)
        self.error.pack(fill="x")

    def toggle(self) -> None:
        self._shown = not self._shown
        self.entry.configure(show="" if self._shown else "•")
        self.eye.configure(image=icons.icon("eye_off" if self._shown else "eye", 18, theme.MUTED))

    def get(self) -> str:
        return self.entry.get().strip() if not self.secret else self.entry.get()

    def set(self, value: str) -> None:
        self.entry.delete(0, "end"); self.entry.insert(0, value)

    def set_error(self, msg: str) -> None:
        self.error.configure(text=msg, text_color=theme.RED)
        self.entry.configure(border_color=theme.RED if msg else theme.BORDER)

    def set_ok(self, msg: str) -> None:
        self.error.configure(text=msg, text_color=theme.EMERALD)
        self.entry.configure(border_color=theme.BORDER)

    def clear(self) -> None:
        self.set_error("")

    def bind_return(self, cb: Callable) -> None:
        self.entry.bind("<Return>", lambda _e: cb())


def info_rows(parent, rows: Iterable[Tuple[str, str]], label_width: int = 170, mono_keys: Tuple[str, ...] = ()) -> None:
    """Vertical label/value list (values may be selectable long hashes)."""
    for i, (k, v) in enumerate(rows):
        ctk.CTkLabel(parent, text=k, font=font(12), text_color=theme.MUTED, anchor="w", width=label_width).grid(
            row=i, column=0, sticky="nw", pady=3, padx=(0, 10))
        ctk.CTkLabel(parent, text=str(v) if v not in (None, "") else "–", font=theme.mono(11) if k in mono_keys else font(13),
                     text_color=theme.TEXT, anchor="w", justify="left", wraplength=470).grid(row=i, column=1, sticky="w", pady=3)


def empty_state(parent, title: str, text: str, kind: str = "inbox") -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text="", image=icons.empty_illustration(kind, 140)).pack(pady=(30, 6))
    ctk.CTkLabel(frame, text=title, font=font(17, "bold"), text_color=theme.TEXT).pack()
    ctk.CTkLabel(frame, text=text, font=font(12), text_color=theme.MUTED, wraplength=420).pack(pady=(2, 30))
    return frame


class Tooltip:
    """Small hover tooltip."""

    def __init__(self, widget, text: str):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _e=None) -> None:
        if self.tip:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{self.widget.winfo_rootx() + 10}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}")
        tk.Label(self.tip, text=self.text, bg=theme.pick(theme.SIDEBAR_BG), fg="#FFFFFF", padx=8, pady=4,
                 font=("TkDefaultFont", 9)).pack()

    def _hide(self, _e=None) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None
