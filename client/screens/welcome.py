"""Welcome / start screen."""
from __future__ import annotations

import customtkinter as ctk

from .. import icons, theme
from ..components.cards import Badge, PrimaryButton, SecondaryButton
from ..theme import font
from .base import PublicScreen


class WelcomeScreen(PublicScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=60, pady=(0, 30))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(0, 30))
        ctk.CTkLabel(left, text="", image=icons.logo(84)).pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(left, text="QMed", font=font(46, "bold"), text_color=theme.PRIMARY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text="Quantum-Secure Medical Data Sharing", font=font(22, "bold"), text_color=theme.TEXT,
                     anchor="w").pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(left, text="Securely simulate quantum key distribution, protect medical documents, and exchange "
                                "files between authenticated users.", font=font(14), text_color=theme.MUTED, anchor="w",
                     justify="left", wraplength=520).pack(anchor="w")
        pills = ctk.CTkFrame(left, fg_color="transparent")
        pills.pack(anchor="w", pady=16)
        pills.grid_propagate(True)
        for text, kind in (("Software Simulation", "teal"), ("No Quantum Hardware Required", "info"), ("Educational Project", "pending")):
            Badge(pills, text, kind).pack(side="left", padx=(0, 6))
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(anchor="w", pady=(6, 0))
        PrimaryButton(row, "Sign In", lambda: app.show_public("login"), "lock", width=150, height=44).pack(side="left", padx=(0, 10))
        SecondaryButton(row, "Create Account", lambda: app.show_public("signup"), "profile", width=170, height=44).pack(side="left", padx=(0, 10))
        SecondaryButton(row, "About QMed", lambda: app.show_public("about"), "about", width=150, height=44).pack(side="left")
        ctk.CTkLabel(left, text="BB84 is simulated in software for educational demonstration. No physical quantum "
                                "hardware is used.", font=font(11), text_color=theme.MUTED, wraplength=470, justify="left",
                     anchor="w").pack(anchor="w", pady=(22, 0))
        ctk.CTkLabel(body, text="", image=icons.hero_illustration(520, 340)).grid(row=0, column=1, sticky="e")
