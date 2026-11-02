"""Settings: local (this computer) vs server-controlled values."""
from __future__ import annotations

import customtkinter as ctk

from common import crypto
from common.bb84 import ALLOWED_BIT_COUNTS
from common.validation import PasswordPolicy, check_password, human_size
from .. import theme
from ..api_client import ApiClient
from ..components.cards import Badge, Card, Field, PageHeader, PrimaryButton, SecondaryButton, DangerButton, info_rows
from ..components.dialogs import Modal, confirm_dialog
from ..config import APP_VERSION
from ..theme import font
from .base import PAD, Screen
from .login import server_dialog


class SettingsScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        PageHeader(self, "Settings", "Local settings apply to this computer only. Server-controlled values are read-only.").pack(
            fill="x", **PAD, pady=(22, 8))
        s = app.settings
        c = self._section("Appearance", "Local")
        seg = ctk.CTkSegmentedButton(c, values=["Light", "Dark"], selected_color=theme.PRIMARY, unselected_color=theme.NEUTRAL_BTN,
                                     text_color=theme.TEXT, command=lambda v: app.set_theme(v.lower()))
        seg.set(s.get("theme").title()); seg.pack(anchor="w", padx=20, pady=(0, 16))

        c = self._section("Security – BB84 (educational parameters)", "Local")
        row = ctk.CTkFrame(c, fg_color="transparent"); row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(row, text="Default BB84 sample size (qubits)", text_color=theme.TEXT).pack(side="left")
        self.bits = ctk.CTkOptionMenu(row, values=[str(b) for b in ALLOWED_BIT_COUNTS], width=100, fg_color=theme.SURFACE_ALT,
                                      button_color=theme.NEUTRAL_BTN, text_color=theme.TEXT,
                                      command=lambda v: s.set(bb84_bits=int(v)))
        self.bits.set(str(s.get("bb84_bits"))); self.bits.pack(side="left", padx=12)
        row = ctk.CTkFrame(c, fg_color="transparent"); row.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(row, text="QBER threshold", text_color=theme.TEXT).pack(side="left")
        self.thr_lbl = ctk.CTkLabel(row, text="", text_color=theme.PRIMARY, font=font(12, "bold")); self.thr_lbl.pack(side="right")
        self.thr = ctk.CTkSlider(row, from_=1, to=30, number_of_steps=29, width=220, progress_color=theme.PRIMARY, command=self._thr)
        self.thr.set(round(float(s.get("qber_threshold")) * 100)); self.thr.pack(side="right", padx=10)
        self._thr(self.thr.get())
        ctk.CTkLabel(c, text="The effective threshold is the lower of this value and the server limit. It is an educational parameter, "
                             "not a universal security policy.", font=font(11), text_color=theme.MUTED, wraplength=850,
                     justify="left").pack(anchor="w", padx=20, pady=(0, 6))
        SecondaryButton(c, "Change Password", self.change_password, "lock").pack(anchor="w", padx=20, pady=(4, 16))

        c = self._section("Server-controlled", "Server")
        self.server_box = ctk.CTkFrame(c, fg_color="transparent"); self.server_box.pack(fill="x", padx=20, pady=(0, 16))

        c = self._section("Connection", "Local")
        self.url = ctk.CTkLabel(c, text="", text_color=theme.TEXT, font=theme.mono(12)); self.url.pack(anchor="w", padx=20)
        row = ctk.CTkFrame(c, fg_color="transparent"); row.pack(anchor="w", padx=20, pady=(8, 16))
        PrimaryButton(row, "Change Server URL", lambda: server_dialog(app, self._refresh)).pack(side="left")
        SecondaryButton(row, "Test Connection", self.test, "refresh").pack(side="left", padx=8)

        c = self._section("Application", "Local")
        ctk.CTkLabel(c, text=f"QMed version {APP_VERSION}  ·  educational BB84 software simulation", text_color=theme.MUTED).pack(anchor="w", padx=20)
        row = ctk.CTkFrame(c, fg_color="transparent"); row.pack(anchor="w", padx=20, pady=(8, 16))
        SecondaryButton(row, "About", lambda: shell.navigate("about"), "about").pack(side="left")
        DangerButton(row, "Clear Local Cache", lambda: confirm_dialog(app, "Clear local cache", "Reset theme, server URL and BB84 defaults on this computer?",
                                                                      self._clear, "Clear", True)).pack(side="left", padx=8)

    def _section(self, title: str, scope: str):
        card = Card(self); card.pack(fill="x", **PAD, pady=6)
        head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=20, pady=(14, 8))
        ctk.CTkLabel(head, text=title, font=font(15, "bold"), text_color=theme.TEXT).pack(side="left")
        Badge(head, scope + (" setting" if scope == "Local" else "-controlled"), "info" if scope == "Local" else "teal").pack(side="left", padx=10)
        return card

    def _thr(self, v) -> None:
        self.thr_lbl.configure(text=f"{int(v)}%")
        self.app.settings.set(qber_threshold=int(v) / 100)

    def on_show(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        cfg = self.app.server_config
        self.url.configure(text=self.app.api.base_url)
        for w in self.server_box.winfo_children():
            w.destroy()
        pol = PasswordPolicy.from_dict(cfg.get("password_policy"))
        info_rows(self.server_box, [("Server QBER limit", f"{cfg['qber_threshold'] * 100:.2f}%"), ("Max file size", human_size(cfg["max_file_bytes"])),
                                    ("Allowed file types", ", ".join(cfg["allowed_extensions"])), ("Session duration", f"{cfg.get('session_hours', 8)} hours"),
                                    ("Password minimum", f"{pol.min_length} characters")], 170)

    def test(self) -> None:
        self.app.check_connection(now=True)
        self.app.run_async(self.app.api.health, lambda h: self.app.notify("success", f"Connected to QMed Server v{h['version']}."))

    def _clear(self) -> None:
        self.app.settings.clear()
        self.app.set_theme("light")
        self.app.api.set_base_url(self.app.settings.get("server_url"))
        self.app.notify("success", "Local cache cleared.")

    def change_password(self) -> None:
        app = self.app
        dlg = Modal(app, "Change password", 480, 470)
        cur, new, conf = Field(dlg, "Current password", secret=True), Field(dlg, "New password", secret=True), Field(dlg, "Confirm new password", secret=True)
        for f in (cur, new, conf):
            f.pack(fill="x", padx=24, pady=(10, 0))
        policy = PasswordPolicy.from_dict(app.server_config.get("password_policy"))

        def submit() -> None:
            for f in (cur, new, conf):
                f.clear()
            problems = check_password(new.get(), policy)
            if not cur.get():
                cur.set_error("Enter your current password."); return
            if problems:
                new.set_error(problems[0]); return
            if new.get() != conf.get():
                conf.set_error("Passwords do not match."); return
            np_, cp = new.get(), cur.get()

            def work():
                blob = crypto.protect_private_key(app.vault.private_key, np_)
                app.api.change_password(cp, np_, blob)

            def ok(_r):
                dlg.destroy(); app.notify("success", "Password updated.")
            app.run_async(work, ok, lambda e: app.handle_error(e))
        PrimaryButton(dlg, "Update Password", submit, width=180).pack(pady=18)
