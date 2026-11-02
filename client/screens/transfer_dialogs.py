"""Transfer details panel and the step-by-step decryption dialog."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from common import crypto
from common.validation import human_size
from .. import icons, theme
from ..components.cards import (Badge, Card, PrimaryButton, SecondaryButton, SuccessButton, info_rows, status_badge)
from ..components.dialogs import Modal, choose_directory
from ..components.loading import LoadingBar
from ..components.tables import fmt_time
from ..encryption import decrypt_received
from ..security import unique_path
from ..theme import font


class TransferDetails(Modal):
    """All transfer metadata (never any secret key material)."""

    def __init__(self, app, t: Dict[str, Any], on_decrypt: Optional[Callable] = None):
        super().__init__(app, f"Transfer {t['id']}", 700, 700)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 6))
        ctk.CTkLabel(head, text=t["original_filename"], font=font(18, "bold"), text_color=theme.TEXT).pack(side="left")
        status_badge(head, t["status"]).pack(side="left", padx=12)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12)
        card = Card(body)
        card.pack(fill="x", padx=8, pady=6)
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=14)
        s, r = t["sender"], t["recipient"]
        qber = "–" if t.get("qber") is None else f"{t['qber'] * 100:.2f}%"
        thr = "–" if t.get("qber_threshold") is None else f"{t['qber_threshold'] * 100:.2f}%"
        info_rows(grid, [
            ("Transfer ID", t["id"]), ("Sender", f"{s['full_name']} (@{s['username']})"),
            ("Recipient", f"{r['full_name']} (@{r['username']})"), ("Sender Role", s["role"]), ("Recipient Role", r["role"]),
            ("File Name", t["original_filename"]), ("File Size", human_size(t["file_size"])),
            ("SHA-256", t.get("original_sha256")), ("Encryption Algorithm", t.get("encryption_algorithm") or "Not encrypted (blocked)"),
            ("Key ID", t.get("key_id")), ("BB84 Simulation", t["bb84_status"].replace("_", " ").title()), ("QBER", qber),
            ("Threshold", thr), ("Eavesdropper Simulation", "ON" if t.get("eve_enabled") else "OFF"),
            ("Integrity Status", t["integrity_status"].title()), ("Created", fmt_time(t["created_at"])),
            ("Updated", fmt_time(t["updated_at"])), ("Current Status", theme.status_label(t["status"])),
            ("Message", t.get("message") or "–")], mono_keys=("SHA-256", "Key ID", "Transfer ID"))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=12)
        if on_decrypt:
            PrimaryButton(row, "Decrypt Document", lambda: (self.destroy(), on_decrypt(t)), "lock").pack(side="left", padx=6)
        SecondaryButton(row, "Close", self.destroy, width=100).pack(side="left", padx=6)


STEPS = ["Authenticate current user", "Retrieve authorized encrypted transfer", "Retrieve key material securely",
         "Decrypt with AES-256-GCM", "Verify authentication tag", "Calculate SHA-256 of recovered file",
         "Compare against expected original hash", "Display result"]


class DecryptDialog(Modal):
    def __init__(self, app, t: Dict[str, Any], on_finished: Callable[[], None]):
        super().__init__(app, f"Decrypt {t['id']}", 680, 720)
        self.t, self.on_finished, self.plaintext = t, on_finished, None
        self.protocol("WM_DELETE_WINDOW", self._close)
        ctk.CTkLabel(self, text="Decrypt Document", font=font(20, "bold"), text_color=theme.TEXT).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text=f"{t['original_filename']}  ·  from {t['sender']['full_name']}", font=font(12),
                     text_color=theme.MUTED).pack(anchor="w", padx=24)
        card = Card(self)
        card.pack(fill="x", padx=24, pady=12)
        self.rows: List[ctk.CTkLabel] = []
        for i, step in enumerate(STEPS, 1):
            lab = ctk.CTkLabel(card, text=f"   {i}. {step}", image=icons.icon("dot", 14, theme.MUTED), compound="left",
                               font=font(13), text_color=theme.MUTED, anchor="w")
            lab.pack(fill="x", padx=16, pady=(8 if i == 1 else 2, 8 if i == len(STEPS) else 2))
            self.rows.append(lab)
        self.loading = LoadingBar(self)
        self.loading.pack(fill="x", padx=24)
        self.result = ctk.CTkFrame(self, fg_color="transparent")
        self.result.pack(fill="both", expand=True, padx=24)
        self.buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons.pack(pady=12)
        self.start_btn = PrimaryButton(self.buttons, "Start Decryption", self.start, "lock")
        self.start_btn.pack(side="left", padx=6)
        SecondaryButton(self.buttons, "Close", self._close, width=100).pack(side="left", padx=6)

    def _mark(self, i: int, state: str) -> None:
        color, name = {"active": (theme.PRIMARY, "dot"), "done": (theme.EMERALD, "check"), "fail": (theme.RED, "error"),
                       "pending": (theme.MUTED, "dot")}[state]
        self.rows[i].configure(image=icons.icon(name, 14, color), text_color=theme.TEXT if state != "pending" else theme.MUTED)

    def start(self) -> None:
        self.start_btn.configure(state="disabled")
        self.loading.start("Decrypting…")
        app, t = self.app, self.t
        step = {"n": 0}

        def advance(i: int) -> None:
            def ui():
                if i > 0:
                    self._mark(i - 1, "done")
                self._mark(i, "active"); step["n"] = i
            app.call_soon(ui)

        def work() -> Dict[str, Any]:
            advance(0); current = app.api.transfer(t["id"])                    # authenticated + authorised
            advance(1); ciphertext = app.api.download(t["id"])
            advance(2); key_info = app.api.key_material(t["id"])
            advance(3); plaintext, sha = decrypt_received(ciphertext, key_info, app.vault.private_key)
            advance(4); advance(5)
            advance(6); verified = sha == key_info["original_sha256"]
            advance(7)
            updated = app.api.report_decryption(t["id"], verified, sha)
            return {"plaintext": plaintext, "sha": sha, "expected": key_info["original_sha256"], "verified": verified,
                    "transfer": updated}

        def ok(res: Dict[str, Any]) -> None:
            for i in range(len(STEPS)):
                self._mark(i, "done" if res["verified"] or i < 6 else "fail")
            self.loading.stop()
            self._show_result(res)
            self.on_finished()

        def fail(exc: Exception) -> None:
            self.loading.stop()
            self._mark(step["n"], "fail")
            if isinstance(exc, crypto.DecryptionError):
                msg = "Authentication failure: the data is corrupted, was modified, or the key does not match."
                app.run_async(lambda: app.api.report_decryption(t["id"], False, "", "Authentication tag verification failed"),
                              lambda _r: self.on_finished(), lambda _e: None)
            else:
                msg = getattr(exc, "message", None) or str(exc) or "Decryption could not be completed."
            for w in self.result.winfo_children():
                w.destroy()
            ctk.CTkLabel(self.result, text="Decryption Failed", font=font(17, "bold"), text_color=theme.RED).pack(anchor="w", pady=(8, 2))
            ctk.CTkLabel(self.result, text=msg, font=font(13), text_color=theme.MUTED, wraplength=600, justify="left").pack(anchor="w")
            self.start_btn.configure(state="normal", text="Try Again")
            if not isinstance(exc, crypto.CryptoError):
                app.handle_error(exc)
        app.run_async(work, ok, fail)

    def _show_result(self, res: Dict[str, Any]) -> None:
        for w in self.result.winfo_children():
            w.destroy()
        self.start_btn.pack_forget()
        good = res["verified"]
        ctk.CTkLabel(self.result, text="Document Decrypted Successfully" if good else "Integrity Verification Failed",
                     font=font(18, "bold"), text_color=theme.EMERALD if good else theme.RED).pack(anchor="w", pady=(6, 4))
        card = Card(self.result)
        card.pack(fill="x")
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=16, pady=10)
        info_rows(grid, [("Original file name", self.t["original_filename"]), ("Recovered file size", human_size(len(res["plaintext"]))),
                         ("Recovered SHA-256", res["sha"]), ("Original SHA-256", res["expected"]),
                         ("Integrity", "VERIFIED" if good else "FAILED")], label_width=150, mono_keys=("Recovered SHA-256", "Original SHA-256"))
        if good:
            self.plaintext = res["plaintext"]
            SuccessButton(self.result, "Save Recovered File", self.save, "download").pack(pady=10)

    def save(self) -> None:
        folder = choose_directory("Choose a folder for the recovered file", self.app.settings.get("last_save_dir"))
        if not folder or self.plaintext is None:
            return
        try:
            path = unique_path(folder, self.t["original_filename"])
            path.write_bytes(self.plaintext)
        except OSError:
            self.app.notify("error", "The file could not be saved to that folder.")
            return
        self.app.settings.set(last_save_dir=folder)
        self.app.notify("success", f"Saved recovered file: {path.name}")

    def _close(self) -> None:
        self.plaintext = None   # drop plaintext from memory
        self.destroy()
