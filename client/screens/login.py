"""Sign-in screen (real backend authentication)."""
from __future__ import annotations

import customtkinter as ctk

from common.crypto import CryptoError
from .. import icons, theme
from ..api_client import ApiError
from ..components.cards import Card, Field, PrimaryButton, SecondaryButton
from ..components.dialogs import Modal
from ..components.loading import LoadingBar
from ..theme import font
from .base import PublicScreen


def server_dialog(app, on_saved=None) -> None:
    dlg = Modal(app, "Server address", 480, 260)
    ctk.CTkLabel(dlg, text="QMed server URL", font=font(16, "bold"), text_color=theme.TEXT).pack(anchor="w", padx=24, pady=(22, 4))
    ctk.CTkLabel(dlg, text="Example for a classroom LAN demo: http://<server-laptop-ip>:5000", font=font(12),
                 text_color=theme.MUTED).pack(anchor="w", padx=24)
    field = Field(dlg, "")
    field.set(app.api.base_url)
    field.pack(fill="x", padx=24, pady=8)

    def save() -> None:
        url = field.get().rstrip("/")
        if not url.startswith(("http://", "https://")):
            field.set_error("The address must start with http:// or https://")
            return
        app.api.set_base_url(url)
        app.settings.set(server_url=url)
        app.connected = None
        app.check_connection(now=True)
        dlg.destroy()
        if on_saved:
            on_saved()
    PrimaryButton(dlg, "Save", save, width=110).pack(pady=8)


class LoginScreen(PublicScreen):
    def __init__(self, parent, app, prefill: str = ""):
        super().__init__(parent, app)
        card = Card(self)
        card.place(relx=.5, rely=.5, anchor="center")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=32)
        ctk.CTkLabel(inner, text="", image=icons.logo(54)).pack()
        ctk.CTkLabel(inner, text="Sign in to QMed", font=font(22, "bold"), text_color=theme.TEXT).pack(pady=(6, 0))
        ctk.CTkLabel(inner, text="Quantum-Secure Medical Data Sharing System", font=font(12), text_color=theme.MUTED).pack(pady=(0, 10))
        self.status = ctk.CTkLabel(inner, text="", font=font(12), text_color=theme.MUTED, compound="left")
        self.status.pack()
        self.ident = Field(inner, "Username or Email", width=340)
        self.ident.pack(fill="x", pady=(12, 0))
        self.password = Field(inner, "Password", secret=True, width=290)
        self.password.pack(fill="x")
        self.ident.bind_return(lambda: self.password.entry.focus())
        self.password.bind_return(self.submit)
        self.loading = LoadingBar(inner)
        self.loading.pack(fill="x", pady=(2, 6))
        self.btn = PrimaryButton(inner, "Sign In", self.submit, "lock", height=42)
        self.btn.pack(fill="x")
        SecondaryButton(inner, "Create Account", lambda: app.show_public("signup"), "profile", height=40).pack(fill="x", pady=(8, 0))
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(row, text="Server settings", width=110, height=24, fg_color="transparent", text_color=theme.PRIMARY,
                      hover_color=theme.SURFACE_ALT, font=font(11), command=lambda: server_dialog(app)).pack(side="left")
        ctk.CTkButton(row, text="← Back", width=60, height=24, fg_color="transparent", text_color=theme.MUTED,
                      hover_color=theme.SURFACE_ALT, font=font(11), command=lambda: app.show_public("welcome")).pack(side="right")
        if prefill:
            self.ident.set(prefill)
            self.password.entry.focus()
        else:
            self.ident.entry.focus()
        app.connection_listeners.append(self._conn)
        self._conn(app.connected)
        if app.connected is None:
            app.check_connection(now=True)

    def _conn(self, ok) -> None:
        if ok is None:
            self.status.configure(text="Connecting to QMed Server…", text_color=theme.MUTED, image=icons.fixed_icon("dot", 12, "#8FA3B3"))
        else:
            self.status.configure(text=f"  {'Connected to QMed Server' if ok else 'Disconnected – check server address'}",
                                  text_color=theme.EMERALD if ok else theme.RED,
                                  image=icons.fixed_icon("dot", 12, "#0F9D6A" if ok else "#C62F2F"))

    def destroy(self) -> None:
        if self._conn in self.app.connection_listeners:
            self.app.connection_listeners.remove(self._conn)
        super().destroy()

    def submit(self) -> None:
        ident, pw = self.ident.get(), self.password.get()
        self.ident.clear(); self.password.clear()
        if not ident:
            self.ident.set_error("Enter your username or email."); return
        if not pw:
            self.password.set_error("Enter your password."); return
        self.btn.configure(state="disabled")
        self.loading.start("Connecting to QMed Server…")
        app = self.app

        def work():
            data = app.api.login(ident, pw)
            try:
                app.vault.unlock(data["encrypted_private_key"], pw)   # unlock encryption key locally
            except CryptoError:
                app.api.logout()
                raise
            return data

        def fail(exc) -> None:
            self.btn.configure(state="normal"); self.loading.stop()
            if isinstance(exc, ApiError) and exc.code == "INVALID_CREDENTIALS":
                self.password.set_error(exc.message)
            else:
                app.handle_error(exc)
        app.run_async(work, app.on_login, fail)
