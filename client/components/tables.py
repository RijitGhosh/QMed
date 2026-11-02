"""Healthcare/cybersecurity style data table built from CustomTkinter widgets (theme-aware)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from .. import theme
from ..theme import font
from .cards import Badge, empty_state


def fmt_time(iso: Optional[str]) -> str:
    if not iso:
        return "–"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%d %b %Y %H:%M")
    except ValueError:
        return iso


class DataTable(ctk.CTkFrame):
    """columns: [{key, title, weight, min, kind}] kind = text | badge | actions | mono.

    Rows are dicts. For a badge column provide row[key] (text) and row[key + '_kind'].
    For an actions column provide row[key] = [(label, callback), ...].
    """

    MAX_ROWS = 200

    def __init__(self, parent, columns: List[Dict[str, Any]], on_row_click: Optional[Callable] = None,
                 empty_title: str = "Nothing here yet", empty_text: str = "", empty_kind: str = "inbox", height: int = 380):
        super().__init__(parent, fg_color=theme.SURFACE, corner_radius=12, border_width=1, border_color=theme.BORDER)
        self.columns, self.on_row_click = columns, on_row_click
        self.head = ctk.CTkFrame(self, fg_color=theme.SURFACE_ALT, corner_radius=10, height=38)
        self.head.pack(fill="x", padx=6, pady=(6, 2))
        self._config_columns(self.head)
        for i, col in enumerate(columns):
            ctk.CTkLabel(self.head, text=col["title"].upper(), font=font(10, "bold"), text_color=theme.MUTED,
                         anchor="w").grid(row=0, column=i, sticky="w", padx=10, pady=8)
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent", height=height)
        self.body.pack(fill="both", expand=True, padx=2, pady=(0, 6))
        self.empty = empty_state(self, empty_title, empty_text, empty_kind)

    def _config_columns(self, frame) -> None:
        for i, col in enumerate(self.columns):
            frame.grid_columnconfigure(i, weight=col.get("weight", 1), minsize=col.get("min", 80))

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        if not rows:
            self.head.pack_forget(); self.body.pack_forget()
            self.empty.pack(fill="both", expand=True)
            return
        self.empty.pack_forget()
        self.head.pack_forget(); self.body.pack_forget()
        self.head.pack(fill="x", padx=6, pady=(6, 2))
        self.body.pack(fill="both", expand=True, padx=2, pady=(0, 6))
        for n, row in enumerate(rows[: self.MAX_ROWS]):
            self._add_row(n, row)

    def _add_row(self, n: int, row: Dict[str, Any]) -> None:
        base = "transparent" if n % 2 == 0 else theme.SURFACE_ALT
        frame = ctk.CTkFrame(self.body, fg_color=base, corner_radius=8, height=42)
        frame.pack(fill="x", padx=4, pady=1)
        self._config_columns(frame)
        clickable = [frame]
        for i, col in enumerate(self.columns):
            kind, value = col.get("kind", "text"), row.get(col["key"], "")
            if kind == "badge":
                w = Badge(frame, str(value), row.get(col["key"] + "_kind", "info"))
                w.grid(row=0, column=i, sticky="w", padx=10, pady=8)
            elif kind == "actions":
                w = ctk.CTkFrame(frame, fg_color="transparent")
                for label, cb in value:
                    ctk.CTkButton(w, text=label, height=26, width=58, corner_radius=6, font=font(11, "bold"),
                                  fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER, text_color=theme.WHITE,
                                  command=cb).pack(side="left", padx=(0, 6))
                w.grid(row=0, column=i, sticky="w", padx=10, pady=7)
            else:
                text = str(value) if value not in (None, "") else "–"
                limit = col.get("max", 34)
                if len(text) > limit:
                    text = text[: limit - 1] + "…"
                w = ctk.CTkLabel(frame, text=text, anchor="w", font=theme.mono(11) if kind == "mono" else font(12),
                                 text_color=theme.TEXT)
                w.grid(row=0, column=i, sticky="w", padx=10, pady=10)
                clickable.append(w)
        if self.on_row_click:
            for widget in clickable:
                widget.bind("<Button-1>", lambda _e, r=row: self.on_row_click(r))
            frame.bind("<Enter>", lambda _e, f=frame: f.configure(fg_color=theme.NEUTRAL_BTN))
            frame.bind("<Leave>", lambda _e, f=frame, b=base: f.configure(fg_color=b))
