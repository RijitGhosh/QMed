"""BB84 Security Lab: independent simulations and the with/without-Eve comparison."""
from __future__ import annotations

import customtkinter as ctk

from common.bb84 import ALLOWED_BIT_COUNTS
from .. import theme
from ..bb84_view import BB84Panel
from ..components.cards import Badge, Card, DangerButton, PageHeader, PrimaryButton, SuccessButton
from ..components.loading import LoadingBar
from ..theme import font
from .about import build_demo_guide
from .base import PAD, Screen

EXPLAIN = ("BB84 uses randomly selected bases to establish shared key material. If an eavesdropper measures and resends quantum "
           "states using incompatible bases, that process introduces detectable errors. QMed simulates this behavior in software "
           "and estimates the resulting Quantum Bit Error Rate (QBER).  This desktop application does not create actual quantum "
           "states. The quantum channel and measurements are simulated mathematically.")


class LabScreen(Screen):
    def __init__(self, parent, app, shell):
        super().__init__(parent, app, shell)
        PageHeader(self, "BB84 Security Lab", "Run the BB84 simulation on its own (no file is sent). Results come from the simulated measurements.").pack(
            fill="x", **PAD, pady=(22, 8))
        info = Card(self, fg_color=theme.SURFACE_ALT); info.pack(fill="x", **PAD, pady=(0, 8))
        ctk.CTkLabel(info, text=EXPLAIN, font=font(12), text_color=theme.MUTED, wraplength=900, justify="left", anchor="w").pack(padx=16, pady=12)
        ctl = Card(self); ctl.pack(fill="x", **PAD, pady=6)
        row = ctk.CTkFrame(ctl, fg_color="transparent"); row.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(row, text="Qubits:", text_color=theme.TEXT).pack(side="left")
        self.bits = ctk.CTkOptionMenu(row, values=[str(b) for b in ALLOWED_BIT_COUNTS], width=90, fg_color=theme.SURFACE_ALT,
                                      button_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)
        self.bits.set(str(app.settings.get("bb84_bits"))); self.bits.pack(side="left", padx=(6, 16))
        self.eve = ctk.CTkSwitch(row, text="Simulate Eavesdropper (Eve)", progress_color=theme.RED, text_color=theme.TEXT,
                                 command=lambda: self.panel.set_eve(bool(self.eve.get())))
        self.eve.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(row, text="QBER threshold:", text_color=theme.TEXT).pack(side="left")
        self.thr_label = ctk.CTkLabel(row, text="", width=52, text_color=theme.PRIMARY, font=font(12, "bold")); self.thr_label.pack(side="right")
        self.thr = ctk.CTkSlider(row, from_=1, to=30, number_of_steps=29, width=150, progress_color=theme.PRIMARY,
                                 command=lambda v: self.thr_label.configure(text=f"{int(v)}%"))
        self.thr.set(round(app.effective_threshold() * 100)); self.thr.pack(side="right", padx=8)
        self.thr_label.configure(text=f"{int(self.thr.get())}%")
        self.run_btn = PrimaryButton(ctl, "Run Simulation", self.run_single, "lab"); self.run_btn.pack(anchor="w", padx=16, pady=(0, 14))
        self.loading = LoadingBar(ctl); self.loading.pack(fill="x", padx=16)
        self.panel = BB84Panel(self, app); self.panel.pack(fill="x", **PAD, pady=8)
        ctk.CTkLabel(self, text="Faculty demonstration: with vs. without Eve", font=font(17, "bold"), text_color=theme.TEXT, anchor="w").pack(
            fill="x", **PAD, pady=(12, 4))
        side = ctk.CTkFrame(self, fg_color="transparent"); side.pack(fill="x", **PAD)
        side.grid_columnconfigure((0, 1), weight=1, uniform="s")
        self.cmp = {}
        for i, (key, title, btn_cls, label) in enumerate((("normal", "Normal Simulation", SuccessButton, "Run Without Eve"),
                                                          ("eve", "Eavesdropper Simulation", DangerButton, "Run With Eve"))):
            c = Card(side); c.grid(row=0, column=i, padx=6, sticky="nsew")
            ctk.CTkLabel(c, text=title, font=font(14, "bold"), text_color=theme.TEXT).pack(anchor="w", padx=16, pady=(14, 0))
            q = ctk.CTkLabel(c, text="QBER: –", font=font(28, "bold"), text_color=theme.MUTED); q.pack(anchor="w", padx=16)
            b = Badge(c, "NOT RUN", "pending"); b.pack(anchor="w", padx=16, pady=4)
            d = ctk.CTkLabel(c, text="", font=font(11), text_color=theme.MUTED); d.pack(anchor="w", padx=16)
            btn_cls(c, label, lambda k=key: self.run_compare(k)).pack(anchor="w", padx=16, pady=14)
            self.cmp[key] = (q, b, d)
        build_demo_guide(self)

    def _params(self):
        return int(self.bits.get()), int(self.thr.get()) / 100

    def run_single(self) -> None:
        bits, thr = self._params()
        eve = bool(self.eve.get())
        self._run(bits, eve, thr, lambda res: self.panel.play(res))

    def _run(self, bits, eve, thr, on_result) -> None:
        self.run_btn.configure(state="disabled"); self.loading.start("Running BB84 simulation…")
        self.panel.set_eve(eve)

        def done(res):
            self.run_btn.configure(state="normal"); self.loading.stop(); on_result(res)

        def fail(e):
            self.run_btn.configure(state="normal"); self.loading.stop(); self.app.handle_error(e)
        self.app.run_async(lambda: self.app.api.simulate_bb84(bits, eve, thr), done, fail)

    def run_compare(self, key: str) -> None:
        bits, thr = self._params()
        bits = max(bits, 1024)          # enough bits for a meaningful comparison
        eve = key == "eve"
        self.eve.select() if eve else self.eve.deselect()

        def show(res):
            self.panel.play(res)
            q, b, d = self.cmp[key]
            passed = res["decision"] == "PASS"
            q.configure(text=f"QBER: {res['qber'] * 100:.2f}%", text_color=theme.EMERALD if passed else theme.RED)
            b.update_kind("PASS" if passed else "WARNING / BLOCKED", "success" if passed else "blocked")
            d.configure(text=f"{res['mismatches']} mismatches in {res['test_sample_size']} sampled bits · threshold {thr * 100:.0f}% · {bits} qubits")
        self._run(bits, eve, thr, show)
