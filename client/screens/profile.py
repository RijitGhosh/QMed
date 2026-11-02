"""Profile page: read-only identity + editable non-security fields."""
from __future__ import annotations

import customtkinter as ctk

from common.validation import validate_email
from .. import theme
from ..components.cards import Badge, Card, Field, PageHeader, PrimaryButton, info_rows
from ..components.tables import fmt_time
from ..theme import font
from .base import PAD, Screen


class ProfileScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        PageHeader(self, "Profile", "Your account details. Security-critical fields cannot be edited here.").pack(fill="x", **PAD, pady=(22, 10))
        self.info = Card(self); self.info.pack(fill="x", **PAD, pady=6)
        self.info_inner = ctk.CTkFrame(self.info, fg_color="transparent"); self.info_inner.pack(fill="x", padx=20, pady=16)
        edit = Card(self); edit.pack(fill="x", **PAD, pady=6)
        ctk.CTkLabel(edit, text="Edit profile", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x", padx=20, pady=(16, 0))
        g = ctk.CTkFrame(edit, fg_color="transparent"); g.pack(fill="x", padx=20, pady=8)
        g.grid_columnconfigure((0, 1), weight=1)
        self.name, self.email = Field(g, "Full Name"), Field(g, "Email")
        self.dept, self.phone = Field(g, "Department / Organization"), Field(g, "Phone")
        for i, f in enumerate((self.name, self.email, self.dept, self.phone)):
            f.grid(row=i // 2, column=i % 2, sticky="ew", padx=6)
        PrimaryButton(edit, "Save Changes", self.save, "check").pack(anchor="w", padx=20, pady=(0, 16))

    def on_show(self) -> None:
        self.app.run_async(self.app.api.profile, self._loaded)

    def _loaded(self, u) -> None:
        self.app.user.update(u)
        self.shell.header.set_user(self.app.user)
        for w in self.info_inner.winfo_children():
            w.destroy()
        info_rows(self.info_inner, [("Full Name", u["full_name"]), ("Username", u["username"]), ("Email", u["email"]),
                                    ("Role", u["role"]), ("Department", u.get("department")), ("Account created", fmt_time(u["created_at"])),
                                    ("Last login", fmt_time(u.get("last_login")))])
        self.name.set(u["full_name"]); self.email.set(u["email"]); self.dept.set(u.get("department") or ""); self.phone.set(u.get("phone") or "")

    def save(self) -> None:
        self.email.clear(); self.name.clear()
        if not self.name.get():
            self.name.set_error("Full name is required."); return
        msg = validate_email(self.email.get())
        if msg:
            self.email.set_error(msg); return
        fields = dict(full_name=self.name.get(), email=self.email.get(), department=self.dept.get(), phone=self.phone.get())
        self.app.run_async(lambda: self.app.api.update_profile(**fields), lambda u: (self._loaded(u), self.app.notify("success", "Profile updated.")))
