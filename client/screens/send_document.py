"""Send Document: 4-step wizard (document -> recipient -> BB84 security -> encrypt & send)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk

from common.crypto import sha256_hex
from common.validation import file_extension, human_size
from .. import theme
from ..api_client import ApiError
from ..bb84_view import BB84Panel
from ..components.cards import (Badge, Card, PageHeader, PrimaryButton, SecondaryButton, SuccessButton, info_rows)
from ..components.dialogs import choose_file
from ..components.loading import LoadingBar
from ..components.tables import fmt_time
from ..encryption import KeyExchange, encrypt_for_recipient, establish_key
from ..security import validate_local_file
from ..theme import font
from .base import PAD, Screen

STEP_NAMES = ["1 Document", "2 Recipient", "3 BB84 Security", "4 Encrypt & Send"]


class SendScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        PageHeader(self, "Send Document", "Encrypt a fictional medical document with a BB84-derived key and send it to another user.").pack(
            fill="x", **PAD, pady=(22, 8))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", **PAD, pady=(0, 8))
        self.step_chips: List[ctk.CTkLabel] = []
        for name in STEP_NAMES:
            c = ctk.CTkLabel(bar, text=f"  {name}  ", height=30, corner_radius=15, font=font(12, "bold"))
            c.pack(side="left", padx=(0, 8))
            self.step_chips.append(c)
        self.stage = ctk.CTkFrame(self, fg_color="transparent")
        self.stage.pack(fill="x", **PAD, pady=(0, 20))
        self.reset()

    # ------------------------------------------------------------- state
    def reset(self) -> None:
        self.path: str = ""; self.plaintext: Optional[bytes] = None; self.sha = ""
        self.users: List[Dict[str, Any]] = []; self.recipient: Optional[Dict[str, Any]] = None
        self.kx: Optional[KeyExchange] = None; self.sent: Optional[Dict[str, Any]] = None
        self.message = ""; self.selected_var = None
        self.step(1)

    def on_show(self) -> None:
        if self.sent:
            self.reset()

    def step(self, n: int) -> None:
        self.current = n
        for w in self.stage.winfo_children():
            w.destroy()
        for i, c in enumerate(self.step_chips, 1):
            done, act = i < n, i == n
            c.configure(fg_color=theme.TEAL if done else theme.PRIMARY if act else theme.NEUTRAL_BTN,
                        text_color=theme.WHITE if done or act else theme.TEXT)
        [None, self._step1, self._step2, self._step3, self._step4][n]()

    def _nav(self, parent, back=None, nxt=None, nxt_text="Next", enabled=True):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(12, 0))
        if back:
            SecondaryButton(row, "← Back", back, width=100).pack(side="left")
        btn = None
        if nxt:
            btn = PrimaryButton(row, nxt_text, nxt, width=160)
            btn.pack(side="right")
            btn.configure(state="normal" if enabled else "disabled")
        return btn

    # ------------------------------------------------------------ step 1
    def _step1(self) -> None:
        card = Card(self.stage); card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent"); inner.pack(fill="x", padx=20, pady=18)
        ctk.CTkLabel(inner, text="Select the medical document", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        ext = ", ".join(self.app.server_config["allowed_extensions"])
        limit = human_size(self.app.server_config["max_file_bytes"])
        ctk.CTkLabel(inner, text=f"Allowed: {ext}  ·  Maximum size: {limit}  ·  Use fictional data only.", font=font(12),
                     text_color=theme.MUTED, anchor="w").pack(fill="x", pady=(2, 10))
        PrimaryButton(inner, "Choose Medical Document", self.pick_file, "upload").pack(anchor="w")
        self.file_info = ctk.CTkFrame(inner, fg_color="transparent"); self.file_info.pack(fill="x", pady=(12, 0))
        self.err = ctk.CTkLabel(inner, text="", font=font(12), text_color=theme.RED, anchor="w"); self.err.pack(fill="x")
        if self.path:
            self._show_file()
        self.next1 = self._nav(inner, nxt=lambda: self.step(2), enabled=bool(self.plaintext))

    def pick_file(self) -> None:
        path = choose_file("Choose a medical document", self.app.server_config["allowed_extensions"])
        if not path:
            return
        msg = validate_local_file(path, tuple(self.app.server_config["allowed_extensions"]), self.app.server_config["max_file_bytes"])
        if msg:
            self.err.configure(text=msg); return
        self.err.configure(text="")
        data = Path(path).read_bytes()
        self.path, self.plaintext, self.sha = path, data, sha256_hex(data)
        self.kx = None
        self.app.run_async(lambda: self.app.api.log_event("FILE_SELECTED", "Document selected for sending."))
        self._show_file()
        self.next1.configure(state="normal")

    def _show_file(self) -> None:
        for w in self.file_info.winfo_children():
            w.destroy()
        g = ctk.CTkFrame(self.file_info, fg_color=theme.SURFACE_ALT, corner_radius=8); g.pack(fill="x")
        inner = ctk.CTkFrame(g, fg_color="transparent"); inner.pack(fill="x", padx=14, pady=10)
        p = Path(self.path)
        info_rows(inner, [("File name", p.name), ("File size", human_size(len(self.plaintext))),
                          ("File type", file_extension(p.name).upper()), ("SHA-256", self.sha)], label_width=100, mono_keys=("SHA-256",))

    # ------------------------------------------------------------ step 2
    def _step2(self) -> None:
        card = Card(self.stage); card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent"); inner.pack(fill="x", padx=20, pady=18)
        ctk.CTkLabel(inner, text="Choose the recipient", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        self.q = ctk.CTkEntry(inner, placeholder_text="Search by username or name…", height=36, fg_color=theme.SURFACE,
                              border_color=theme.BORDER, text_color=theme.TEXT)
        self.q.pack(fill="x", pady=8)
        self.q.bind("<KeyRelease>", lambda _e: self._render_users())
        self.user_list = ctk.CTkScrollableFrame(inner, height=190, fg_color=theme.SURFACE_ALT)
        self.user_list.pack(fill="x")
        ctk.CTkLabel(inner, text="Optional message", font=font(12, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x", pady=(10, 2))
        self.msg = ctk.CTkTextbox(inner, height=70, fg_color=theme.SURFACE, border_width=1, border_color=theme.BORDER, text_color=theme.TEXT)
        self.msg.pack(fill="x"); self.msg.insert("1.0", self.message)
        self.err2 = ctk.CTkLabel(inner, text="", font=font(12), text_color=theme.RED, anchor="w"); self.err2.pack(fill="x")
        self._nav(inner, back=lambda: self.step(1), nxt=self._to_step3)
        self.app.run_async(self.app.api.users, self._users_loaded)

    def _users_loaded(self, users) -> None:
        self.users = users
        self._render_users()

    def _render_users(self) -> None:
        for w in self.user_list.winfo_children():
            w.destroy()
        q = self.q.get().strip().lower()
        shown = [u for u in self.users if q in u["username"].lower() or q in u["full_name"].lower()]
        if not shown:
            ctk.CTkLabel(self.user_list, text="No matching registered users.", text_color=theme.MUTED).pack(pady=20)
        for u in shown:
            active = self.recipient and self.recipient["id"] == u["id"]
            row = ctk.CTkButton(self.user_list, text=f"{u['full_name']}   @{u['username']}   —   {u['role']}", anchor="w", height=38,
                                fg_color=theme.PRIMARY if active else "transparent", hover_color=theme.NEUTRAL_BTN_HOVER,
                                text_color=theme.WHITE if active else theme.TEXT, command=lambda u=u: self._choose(u))
            row.pack(fill="x", pady=1)

    def _choose(self, u) -> None:
        self.recipient = u
        self._render_users()

    def _to_step3(self) -> None:
        if not self.recipient:
            self.err2.configure(text="Select a recipient to continue."); return
        self.message = self.msg.get("1.0", "end").strip()[:500]
        self.step(3)

    # ------------------------------------------------------------ step 3
    def _step3(self) -> None:
        card = Card(self.stage); card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent"); inner.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(inner, text="BB84 security check (software simulation)", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(inner, text="No physical quantum hardware is used. The key for this transfer is derived from the sifted key "
                                 "with HKDF-SHA256 only if the QBER test passes.", font=font(12), text_color=theme.MUTED, anchor="w",
                     justify="left", wraplength=880).pack(fill="x", pady=(2, 8))
        ctl = ctk.CTkFrame(inner, fg_color="transparent"); ctl.pack(fill="x")
        ctk.CTkLabel(ctl, text="Qubits:", text_color=theme.TEXT).pack(side="left")
        default = str(max(512, int(self.app.settings.get("bb84_bits"))))
        self.bits = ctk.CTkOptionMenu(ctl, values=["512", "1024", "2048"], width=90, fg_color=theme.SURFACE_ALT,
                                      button_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)
        self.bits.set(default if default in ("512", "1024", "2048") else "512"); self.bits.pack(side="left", padx=(6, 18))
        self.eve = ctk.CTkSwitch(ctl, text="Simulate Eavesdropper (Eve)", progress_color=theme.RED, text_color=theme.TEXT,
                                 command=lambda: self.panel.set_eve(bool(self.eve.get())))
        self.eve.pack(side="left", padx=(0, 18))
        ctk.CTkLabel(ctl, text=f"QBER threshold: {self.app.effective_threshold() * 100:.2f}% (configurable educational parameter)",
                     text_color=theme.MUTED, font=font(12)).pack(side="left")
        self.run_btn = PrimaryButton(inner, "Run BB84 Security Check", self.run_bb84, "shield")
        self.run_btn.pack(anchor="w", pady=(10, 0))
        self.loading = LoadingBar(inner); self.loading.pack(fill="x")
        self.panel = BB84Panel(self.stage, self.app, table_rows=8, compact=True)
        self.panel.pack(fill="x", pady=(10, 0))
        self.verdict = ctk.CTkLabel(self.stage, text="", font=font(13, "bold"), anchor="w", justify="left", wraplength=900)
        self.verdict.pack(fill="x", pady=(8, 0))
        self.nav3 = self._nav(self.stage, back=lambda: self.step(2), nxt=lambda: self.step(4), nxt_text="Continue", enabled=False)

    def run_bb84(self) -> None:
        self.run_btn.configure(state="disabled"); self.nav3.configure(state="disabled")
        self.verdict.configure(text=""); self.loading.start("Running BB84 simulation…")
        eve, bits, thr, app = bool(self.eve.get()), int(self.bits.get()), self.app.effective_threshold(), self.app
        self.panel.set_eve(eve)

        def work():
            app.api.log_event("BB84_STARTED", f"Transfer BB84: {bits} qubits, Eve {'ON' if eve else 'OFF'}.")
            return establish_key(bits, eve, thr)

        def ok(kx: KeyExchange) -> None:
            self.kx = kx
            self.loading.start("Deriving secure key…" if kx.result.key_material_ok else "Evaluating result…")
            self.panel.play(kx.result.to_public_dict(table_limit=8), on_done=self._bb84_done)

        def fail(e):
            self.run_btn.configure(state="normal"); self.loading.stop(); app.handle_error(e)
        app.run_async(work, ok, fail)

    def _bb84_done(self) -> None:
        kx = self.kx
        self.run_btn.configure(state="normal"); self.loading.stop()
        if kx.usable:
            self.verdict.configure(text="✓ Security Check Passed  ·  Key Agreement: Confirmed (key hidden)", text_color=theme.EMERALD)
            self.nav3.configure(state="normal")
            return
        r = kx.result
        if r.decision == "POSSIBLE_EAVESDROPPING":
            why = "The simulated QBER exceeded the configured threshold. Transfer blocked. The key exchange was aborted and nothing was uploaded."
        elif not r.key_material_ok and r.decision == "PASS":
            why = "Not enough secret key material after sifting. Increase the number of qubits and run again."
        else:
            why = "Key confirmation failed (residual errors). Transfer aborted; run BB84 again."
        self.verdict.configure(text="⚠ " + why, text_color=theme.RED)
        self.app.notify("warning", why)
        if r.test_sample_size:
            meta = {"recipient_id": self.recipient["id"], "original_filename": Path(self.path).name,
                    "file_size": len(self.plaintext), "original_sha256": self.sha, "message": self.message, "bb84": kx.report()}
            self.app.run_async(lambda: self.app.api.report_blocked(meta), lambda _t: None, lambda _e: None)

    # ------------------------------------------------------------ step 4
    def _step4(self) -> None:
        card = Card(self.stage); card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent"); inner.pack(fill="x", padx=20, pady=18)
        self.body4 = inner
        ctk.CTkLabel(inner, text="Encrypt & send", font=font(16, "bold"), text_color=theme.TEXT, anchor="w").pack(fill="x")
        g = ctk.CTkFrame(inner, fg_color=theme.SURFACE_ALT, corner_radius=8); g.pack(fill="x", pady=8)
        gi = ctk.CTkFrame(g, fg_color="transparent"); gi.pack(fill="x", padx=14, pady=10)
        info_rows(gi, [("Recipient", f"{self.recipient['full_name']} ({self.recipient['role']})"), ("File", Path(self.path).name),
                       ("Size", human_size(len(self.plaintext))), ("Algorithm", "AES-256-GCM (key from BB84 + HKDF-SHA256)"),
                       ("QBER", f"{self.kx.result.qber * 100:.2f}%"), ("Original SHA-256", self.sha)], 130, ("Original SHA-256",))
        self.loading4 = LoadingBar(inner); self.loading4.pack(fill="x")
        row = ctk.CTkFrame(inner, fg_color="transparent"); row.pack(fill="x", pady=(8, 0))
        SecondaryButton(row, "← Back", lambda: self.step(3), width=100).pack(side="left")
        self.send_btn = SuccessButton(row, "Encrypt & Send", self.send, "lock", width=190)
        self.send_btn.pack(side="right")

    def send(self) -> None:
        self.send_btn.configure(state="disabled"); self.loading4.start("Encrypting document…")
        app, kx, rec = self.app, self.kx, self.recipient
        plain, name, msg = self.plaintext, Path(self.path).name, self.message

        def work():
            ct, meta = encrypt_for_recipient(plain, name, app.user["id"], rec["id"], rec["public_key"], kx, msg)
            app.call_soon(lambda: self.loading4.start("Uploading encrypted document…"))
            return app.api.upload_transfer(ct, meta)      # success is only claimed after the server confirms

        def ok(t):
            self.sent = t; self.loading4.stop(); self._confirmation(t)

        def fail(e):
            self.send_btn.configure(state="normal"); self.loading4.stop(); app.handle_error(e)
        app.run_async(work, ok, fail)

    def _confirmation(self, t: Dict[str, Any]) -> None:
        for w in self.body4.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.body4, text="Document Sent Successfully", font=font(20, "bold"), text_color=theme.EMERALD, anchor="w").pack(fill="x")
        Badge(self.body4, "Encrypted & Sent", "success").pack(anchor="w", pady=6)
        g = ctk.CTkFrame(self.body4, fg_color="transparent"); g.pack(fill="x")
        info_rows(g, [("Transfer ID", t["id"]), ("Recipient", f"{t['recipient']['full_name']} ({t['recipient']['role']})"),
                      ("File name", t["original_filename"]), ("Timestamp", fmt_time(t["created_at"])), ("File size", human_size(t["file_size"])),
                      ("Encryption", t["encryption_algorithm"]), ("QBER", f"{t['qber'] * 100:.2f}%"), ("BB84 status", "PASSED"),
                      ("Integrity hash (SHA-256)", t["original_sha256"])], 190, ("Transfer ID", "Integrity hash (SHA-256)"))
        row = ctk.CTkFrame(self.body4, fg_color="transparent"); row.pack(fill="x", pady=(10, 0))
        PrimaryButton(row, "Send Another Document", self.reset, "send").pack(side="left")
        SecondaryButton(row, "View Sent Files", lambda: self.shell.navigate("sent")).pack(side="left", padx=8)
        self.app.notify("success", "Document sent successfully.")
