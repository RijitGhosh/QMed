"""About QMed: overview, how it works, threat model, limitations and the faculty demo guide."""
from __future__ import annotations

import customtkinter as ctk

from .. import theme
from ..components.cards import Card, PageHeader, SecondaryButton
from ..config import APP_VERSION
from ..theme import font
from .base import PAD, PublicScreen, Screen

SECTIONS = [
    ("Why QMed?", "Medical documents are sensitive. QMed shows, end to end, how a document can be protected with "
                  "authenticated encryption and how a BB84-style key exchange can detect an eavesdropper. Any "
                  "registered user (Doctor, Patient or Other) can send to any other registered user - roles describe "
                  "identity, they do not fix who may send or receive."),
    ("How BB84 Works", "BB84 uses randomly selected bases to establish shared key material. If an eavesdropper measures "
                       "and resends quantum states using incompatible bases, that process introduces detectable errors. "
                       "QMed simulates this behaviour in software and estimates the resulting Quantum Bit Error Rate (QBER).\n\n"
                       "1. Alice generates random bits and random bases.\n2. Bob measures with his own random bases.\n"
                       "3. Eve (optional) measures and resends with random bases.\n4. Alice and Bob publicly compare bases "
                       "and keep only the positions where they match (the sifted key).\n5. A random sample of the sifted key is "
                       "compared: QBER = mismatched sampled bits / sampled bits.\n6. If QBER is above the configured "
                       "threshold the exchange is aborted and the transfer is blocked.\n\nThis desktop application does not "
                       "create actual quantum states. The quantum channel and measurements are simulated mathematically."),
    ("How File Encryption Works", "Password -> scrypt hash (login only).  BB84 sifted key -> test bits removed -> HKDF-SHA256 -> "
                                  "256-bit key -> AES-256-GCM encryption of the document on the sender's computer.  Original SHA-256 is "
                                  "stored as integrity metadata; after decryption the recovered SHA-256 is compared with it.  The "
                                  "file key is wrapped for the recipient (X25519 + HKDF + AES-GCM) so the server stores only ciphertext "
                                  "and a wrapped key it cannot open."),
    ("Threat Demonstration", "Enable 'Simulate Eavesdropper (Eve)' in the BB84 Security Lab or in the Send Document workflow. Eve's "
                             "intercept-resend attack disturbs about 25% of the sifted bits, so QBER rises far above the threshold, "
                             "the key exchange is aborted, no document is uploaded and an audit event is recorded."),
    ("Security Model", "Considered threats: unauthorised login (scrypt hashing, random salts, throttling, expiring server-side "
                       "tokens); access to another user's documents (per-transfer authorisation); tampering with ciphertext or "
                       "metadata (AES-GCM tag + authenticated metadata); path traversal and unsafe uploads (random server-side file "
                       "names, extension and size checks); simulated eavesdropping on the key exchange (QBER test).\n\n"
                       "Trust model / prototype limitation: the server relays the recipient's wrapped key and, at login, receives "
                       "the account password, so a malicious server operator is out of scope. Traffic is plain HTTP on a trusted "
                       "classroom network."),
    ("Limitations", "QMed is an educational student project. It is NOT clinically certified, NOT HIPAA/GDPR certified, NOT real "
                    "quantum communication and NOT production-ready healthcare infrastructure. BB84 is simulated in software; no "
                    "physical quantum hardware is used. Real deployment would need TLS, hardened key management, independent "
                    "security review, backups, monitoring and regulatory compliance."),
    ("Educational Use", "Use only fictional documents. Never upload real patient data. The QBER threshold is an educational parameter, "
                        "not a clinical security policy."),
]
DEMO_STEPS = [
    "Create a Doctor account (Create Account -> role Doctor).", "Create a Patient account.",
    "Sign in and open BB84 Security Lab -> Run Without Eve: QBER stays about 0% (PASS).",
    "Send Document: choose a fictional report, choose the Patient, run BB84 (Eve OFF), encrypt & send.",
    "Sign out and sign in as the Patient on the same computer.",
    "Inbox -> Decrypt: the file is decrypted locally.", "Compare the original and recovered SHA-256 hashes (Integrity: VERIFIED).",
    "Back in the Security Lab / Send workflow, switch Simulate Eavesdropper (Eve) ON.", "Run BB84 again.",
    "Observe QBER of roughly 25%: 'Potential Eavesdropping Detected' and the transfer is blocked."]


def build_about(parent, back=None) -> None:
    head = PageHeader(parent, "About QMed", "QMed is an educational software platform demonstrating secure medical-document "
                                           "exchange using conventional authenticated encryption and a simulated BB84 quantum "
                                           "key distribution workflow.")
    head.pack(fill="x", **PAD, pady=(20, 6))
    if back:
        SecondaryButton(head.actions, "← Back", back, width=90).pack()
    note = Card(parent, fg_color=theme.SURFACE_ALT)
    note.pack(fill="x", **PAD, pady=(6, 8))
    ctk.CTkLabel(note, text="No quantum hardware is used. BB84 is simulated in software for educational demonstration.",
                 font=font(13, "bold"), text_color=theme.PRIMARY, wraplength=900, justify="left").pack(padx=16, pady=12, anchor="w")
    for title, text in SECTIONS:
        c = Card(parent)
        c.pack(fill="x", **PAD, pady=6)
        ctk.CTkLabel(c, text=title, font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(c, text=text, font=font(13), text_color=theme.MUTED, anchor="w", justify="left", wraplength=900).pack(
            fill="x", padx=18, pady=(0, 14))
    build_demo_guide(parent)
    ctk.CTkLabel(parent, text=f"QMed version {APP_VERSION}", font=font(11), text_color=theme.MUTED).pack(pady=14)


def build_demo_guide(parent) -> None:
    c = Card(parent)
    c.pack(fill="x", **PAD, pady=6)
    ctk.CTkLabel(c, text="Demo Guide (faculty demonstration)", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(
        fill="x", padx=18, pady=(14, 4))
    for i, step in enumerate(DEMO_STEPS, 1):
        ctk.CTkLabel(c, text=f"Demonstration {i}:  {step}", font=font(13), text_color=theme.MUTED, anchor="w", justify="left",
                     wraplength=900).pack(fill="x", padx=18, pady=2)
    ctk.CTkLabel(c, text="", height=8).pack()


class AboutScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        build_about(self)


class PublicAbout(PublicScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        build_about(scroll, back=lambda: app.show_public("welcome"))
