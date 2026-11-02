"""Registration screen with live password-strength feedback."""
from __future__ import annotations

import customtkinter as ctk

from common.validation import (ROLES, PasswordPolicy, check_password, password_strength, validate_email,
                               validate_username)
from .. import icons, theme
from ..api_client import ApiError
from ..components.cards import Card, Field, PrimaryButton, SecondaryButton
from ..components.loading import LoadingBar
from ..encryption import new_account_keys
from ..theme import font
from .base import PublicScreen

_STRENGTH_COLORS = [theme.RED, theme.RED, theme.AMBER, theme.TEAL, theme.EMERALD]


class SignupScreen(PublicScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True)
        card = Card(outer)
        card.pack(pady=(0, 24))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=28)
        ctk.CTkLabel(inner, text="Create your QMed account", font=font(22, "bold"), text_color=theme.TEXT).pack()
        ctk.CTkLabel(inner, text="An encryption key pair is generated on this computer and protected with your password.",
                     font=font(12), text_color=theme.MUTED).pack(pady=(0, 10))
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack()
        self.name = Field(grid, "Full Name", width=300); self.username = Field(grid, "Username", width=300)
        self.email = Field(grid, "Email", width=300); self.dept = Field(grid, "Department / Organization (optional)", width=300)
        self.phone = Field(grid, "Phone (optional)", width=300)
        self.password = Field(grid, "Password", secret=True, width=250); self.confirm = Field(grid, "Confirm Password", secret=True, width=250)
        for i, f in enumerate((self.name, self.username, self.email, self.dept)):
            f.grid(row=i // 2, column=i % 2, padx=10, sticky="ew")
        self.phone.grid(row=2, column=0, padx=10, sticky="ew")
        roles = ctk.CTkFrame(grid, fg_color="transparent")
        roles.grid(row=2, column=1, padx=10, sticky="ew")
        ctk.CTkLabel(roles, text="Role", font=font(12, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        self.role = ctk.CTkSegmentedButton(roles, values=list(ROLES), height=38, selected_color=theme.PRIMARY,
                                           selected_hover_color=theme.PRIMARY_HOVER, unselected_color=theme.NEUTRAL_BTN,
                                           unselected_hover_color=theme.NEUTRAL_BTN_HOVER, text_color=theme.TEXT)
        self.role.set(ROLES[1]); self.role.pack(fill="x", pady=(4, 0))
        self.password.grid(row=3, column=0, padx=10, sticky="ew"); self.confirm.grid(row=3, column=1, padx=10, sticky="ew")
        meter = ctk.CTkFrame(grid, fg_color="transparent")
        meter.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))
        self.bar = ctk.CTkProgressBar(meter, height=8, fg_color=theme.SURFACE_ALT)
        self.bar.pack(side="left", fill="x", expand=True); self.bar.set(0)
        self.strength = ctk.CTkLabel(meter, text="Strength: –", font=font(11), text_color=theme.MUTED, width=120, anchor="e")
        self.strength.pack(side="left")
        self.policy = PasswordPolicy.from_dict(app.server_config.get("password_policy"))
        rules = f"At least {self.policy.min_length} characters with upper- and lower-case letters and a digit" + \
                (" and a symbol." if self.policy.require_symbol else ".")
        ctk.CTkLabel(inner, text=rules, font=font(11), text_color=theme.MUTED).pack()
        self.password.entry.bind("<KeyRelease>", lambda _e: self._live())
        self.confirm.entry.bind("<KeyRelease>", lambda _e: self._live())
        self.loading = LoadingBar(inner); self.loading.pack(fill="x", pady=(8, 0))
        row = ctk.CTkFrame(inner, fg_color="transparent"); row.pack(pady=(6, 0))
        self.btn = PrimaryButton(row, "Create Account", self.submit, "shield", width=190, height=42)
        self.btn.pack(side="left", padx=6)
        SecondaryButton(row, "Back to Sign In", lambda: app.show_public("login"), width=160, height=42).pack(side="left", padx=6)

    def _live(self) -> None:
        pw = self.password.get()
        score, label = password_strength(pw)
        self.bar.configure(progress_color=_STRENGTH_COLORS[score]); self.bar.set(score / 4 if pw else 0)
        self.strength.configure(text=f"Strength: {label}")
        problems = check_password(pw, self.policy) if pw else []
        if pw and problems:
            self.password.set_error(problems[0])
        elif pw:
            self.password.set_ok("✓ Password accepted")
        else:
            self.password.clear()
        if self.confirm.get():
            self.confirm.set_error("" if self.confirm.get() == pw else "Passwords do not match.")

    def submit(self) -> None:
        for f in (self.name, self.username, self.email, self.password, self.confirm):
            f.clear()
        errors = 0
        checks = [(self.name, "Full name is required." if not self.name.get() else None),
                  (self.username, validate_username(self.username.get())), (self.email, validate_email(self.email.get()))]
        problems = check_password(self.password.get(), self.policy)
        checks.append((self.password, problems[0] if problems else None))
        checks.append((self.confirm, None if self.confirm.get() == self.password.get() else "Passwords do not match."))
        for field, msg in checks:
            if msg:
                field.set_error(msg); errors += 1
        if errors:
            return
        password = self.password.get()
        payload = {"full_name": self.name.get(), "username": self.username.get(), "email": self.email.get(),
                   "password": password, "role": self.role.get(), "department": self.dept.get(), "phone": self.phone.get()}
        self.btn.configure(state="disabled"); self.loading.start("Generating encryption keys and creating account…")
        app = self.app

        def work():
            pub, blob = new_account_keys(password)
            return app.api.register({**payload, "public_key": pub, "encrypted_private_key": blob})

        def done(_):
            app.notify("success", "Account created. You can now sign in.")
            app.show_public("login", prefill=payload["username"])

        def fail(exc):
            self.btn.configure(state="normal"); self.loading.stop()
            if isinstance(exc, ApiError) and exc.code == "USERNAME_TAKEN":
                self.username.set_error(exc.message)
            elif isinstance(exc, ApiError) and exc.code == "EMAIL_TAKEN":
                self.email.set_error(exc.message)
            else:
                app.handle_error(exc)
        app.run_async(work, done, fail)
