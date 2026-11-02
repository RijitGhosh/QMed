"""Interactive BB84 visualisation: Alice -> (Eve) -> Bob, stage tracker, statistics and sample table."""
from __future__ import annotations

import math
import tkinter as tk
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from common.bb84 import DECISION_PASS
from . import theme
from .components.cards import Badge, Card
from .components.tables import DataTable
from .theme import font, pick

STAGES = ["Alice generates random bits", "Alice selects random bases", "Bob selects random bases",
          "Simulated quantum transmission", "Eve intercept-resend (optional)", "Alice and Bob compare bases",
          "Sifted key is generated", "Sample compared to estimate QBER", "Security decision is made"]
TICKS_PER_STAGE, TICK_MS = 6, 60


class BB84Panel(ctk.CTkFrame):
    def __init__(self, parent, app, table_rows: int = 12, compact: bool = False):
        super().__init__(parent, fg_color="transparent")
        self.app, self.table_rows = app, table_rows
        self.eve, self.stage, self.tick, self.state = False, 0, 0, "idle"   # idle | running | pass | fail
        self._job: Optional[str] = None
        self._result: Optional[Dict[str, Any]] = None
        self._done_cb: Optional[Callable[[], None]] = None

        card = Card(self)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="Simulated quantum channel", font=font(14, "bold"), text_color=theme.TEXT, anchor="w").pack(
            fill="x", padx=16, pady=(12, 0))
        self.canvas = tk.Canvas(card, height=150, highlightthickness=0, bd=0, bg=pick(theme.SURFACE))
        self.canvas.pack(fill="x", padx=12, pady=(4, 0))
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.pack(fill="x", padx=16, pady=(4, 0))
        self.chips = []
        for i in range(len(STAGES)):
            c = ctk.CTkLabel(chips, text=str(i + 1), width=28, height=28, corner_radius=14, font=font(11, "bold"),
                             fg_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)
            c.pack(side="left", padx=(0, 6))
            self.chips.append(c)
        self.caption = ctk.CTkLabel(card, text="Ready. Run a simulation to see each BB84 stage.", font=font(12),
                                    text_color=theme.MUTED, anchor="w")
        self.caption.pack(fill="x", padx=16, pady=(6, 12))

        self.result_card = Card(self)
        self.result_card.pack(fill="x", pady=(12, 0))
        top = ctk.CTkFrame(self.result_card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))
        self.decision_label = ctk.CTkLabel(top, text="No result yet", font=font(16, "bold"), text_color=theme.MUTED)
        self.decision_label.pack(side="left")
        self.decision_badge = Badge(top, "IDLE", "pending")
        self.decision_badge.pack(side="left", padx=12)
        grid = ctk.CTkFrame(self.result_card, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 12))
        self.stat = {}
        names = ["Raw key length", "Sifted key length", "Test sample size", "Matching bits", "Mismatching bits",
                 "QBER", "Threshold", "Key material left"]
        for i, n in enumerate(names):
            cell = ctk.CTkFrame(grid, fg_color=theme.SURFACE_ALT, corner_radius=8)
            cell.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="nsew")
            grid.grid_columnconfigure(i % 4, weight=1)
            ctk.CTkLabel(cell, text=n, font=font(10), text_color=theme.MUTED, anchor="w").pack(fill="x", padx=10, pady=(6, 0))
            self.stat[n] = ctk.CTkLabel(cell, text="–", font=font(16, "bold"), text_color=theme.TEXT, anchor="w")
            self.stat[n].pack(fill="x", padx=10, pady=(0, 6))

        self.table_note = ctk.CTkLabel(self, text="", font=font(11), text_color=theme.MUTED, anchor="w")
        self.table = DataTable(self, [
            {"key": "position", "title": "Position", "weight": 1, "min": 70},
            {"key": "alice_bit", "title": "Alice bit", "weight": 1, "min": 70},
            {"key": "alice_basis", "title": "Alice basis", "weight": 1, "min": 80},
            {"key": "bob_basis", "title": "Bob basis", "weight": 1, "min": 80},
            {"key": "bob_result", "title": "Bob result", "weight": 1, "min": 80},
            {"key": "kept", "title": "Kept?", "weight": 1, "min": 90, "kind": "badge"}],
            empty_title="No simulation yet", empty_text="Run BB84 to see the sample of transmitted qubits.",
            empty_kind="sent", height=240 if not compact else 180)
        self.table_note.pack(fill="x", pady=(12, 2))
        self.table.pack(fill="x")
        self.table.set_rows([])
        app.theme_listeners.append(self.redraw)

    def destroy(self) -> None:
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        if self.redraw in self.app.theme_listeners:
            self.app.theme_listeners.remove(self.redraw)
        super().destroy()

    # ------------------------------------------------------------- drawing
    def redraw(self) -> None:
        c = self.canvas
        try:
            c.configure(bg=pick(theme.SURFACE))
        except tk.TclError:
            return
        c.delete("all")
        w, h = max(c.winfo_width(), 600), 150
        text, muted, blue, teal = pick(theme.TEXT), pick(theme.MUTED), pick(theme.PRIMARY), pick(theme.TEAL)
        red, border = pick(theme.RED), pick(theme.BORDER)
        alt = pick(theme.SURFACE_ALT)
        ax, bx, cy, bw, bh = 90, w - 90, 78, 110, 62

        def box(x, label, sub, color, dashed=False):
            c.create_rectangle(x - bw / 2, cy - bh / 2, x + bw / 2, cy + bh / 2, fill=alt, outline=color, width=2,
                               dash=(4, 3) if dashed else ())
            c.create_text(x, cy - 8, text=label, fill=text if not dashed else muted, font=("TkDefaultFont", 12, "bold"))
            c.create_text(x, cy + 14, text=sub, fill=muted, font=("TkDefaultFont", 9))

        c.create_line(ax + bw / 2, cy, bx - bw / 2, cy, fill=teal if self.state != "fail" else red, width=3, dash=(8, 5))
        c.create_text(w / 2, 24, text="Quantum channel (simulated in software)", fill=muted, font=("TkDefaultFont", 10))
        box(ax, "Alice", "sender", blue)
        box(bx, "Bob", "receiver", teal)
        if self.eve:
            box(w / 2, "Eve", "intercept-resend", red)
        else:
            box(w / 2, "Eve", "OFF", border, dashed=True)
        if self.state == "running" and self.stage >= 4:
            # animated photons travelling Alice -> (Eve) -> Bob
            span = (bx - bw / 2) - (ax + bw / 2)
            for k in range(5):
                p = ((self.tick * 0.03) + k / 5) % 1.0
                x = ax + bw / 2 + p * span
                if self.eve and abs(x - w / 2) < bw / 2:
                    continue
                r = 5 + 2 * math.sin(p * math.pi * 4)
                c.create_oval(x - r, cy - r, x + r, cy + r, fill=blue if p < .5 or not self.eve else red, outline="")
        if self.state in ("pass", "fail"):
            msg, col = ("Key exchange secure", teal) if self.state == "pass" else ("Interference detected", red)
            c.create_text(w / 2, cy + bh / 2 + 22, text=msg, fill=col, font=("TkDefaultFont", 11, "bold"))

    def _paint_chips(self) -> None:
        for i, chip in enumerate(self.chips):
            skipped = i == 4 and not self.eve
            if skipped and self.stage > i:
                chip.configure(fg_color=theme.NEUTRAL_BTN, text_color=theme.MUTED)
            elif self.stage > i + 1 or (self.stage == len(STAGES) and self.state != "running"):
                chip.configure(fg_color=theme.TEAL, text_color=theme.WHITE)
            elif self.stage == i + 1:
                chip.configure(fg_color=theme.PRIMARY, text_color=theme.WHITE)
            else:
                chip.configure(fg_color=theme.NEUTRAL_BTN, text_color=theme.TEXT)

    # ------------------------------------------------------------ control
    def set_eve(self, on: bool) -> None:
        self.eve = on
        self.redraw()

    def reset(self) -> None:
        if self._job:
            self.after_cancel(self._job); self._job = None
        self.state, self.stage, self.tick, self._result = "idle", 0, 0, None
        self.caption.configure(text="Ready. Run a simulation to see each BB84 stage.")
        self.decision_label.configure(text="No result yet", text_color=theme.MUTED)
        self.decision_badge.update_kind("IDLE", "pending")
        for v in self.stat.values():
            v.configure(text="–", text_color=theme.TEXT)
        self.table.set_rows([]); self.table_note.configure(text="")
        self._paint_chips(); self.redraw()

    def play(self, result: Dict[str, Any], on_done: Optional[Callable[[], None]] = None, animate: bool = True) -> None:
        """Progressively display the stages, then reveal the numbers computed by the simulation."""
        self.reset()
        self.eve = bool(result.get("eve_enabled"))
        self._result, self._done_cb = result, on_done
        if not animate:
            self.stage, self.state = len(STAGES), "running"
            self._finish()
            return
        self.state = "running"
        self._tick()

    def _tick(self) -> None:
        self.tick += 1
        new_stage = min(len(STAGES), self.tick // TICKS_PER_STAGE + 1)
        if new_stage != self.stage:
            self.stage = new_stage
            label = STAGES[new_stage - 1] + (" – skipped (Eve is OFF)" if new_stage == 5 and not self.eve else "")
            self.caption.configure(text=f"Stage {new_stage}/{len(STAGES)}: {label}")
            self._paint_chips()
        self.redraw()
        if self.tick >= TICKS_PER_STAGE * len(STAGES):
            self._finish()
        else:
            self._job = self.after(TICK_MS, self._tick)

    def _finish(self) -> None:
        self._job = None
        r = self._result or {}
        passed = r.get("decision") == DECISION_PASS
        self.state = "pass" if passed else "fail"
        self.stage = len(STAGES)
        self._paint_chips()
        insufficient = r.get("decision") == "INSUFFICIENT_DATA"
        qber, thr = r.get("qber", 0.0) * 100, r.get("threshold", 0.0) * 100
        self.stat["Raw key length"].configure(text=str(r.get("bit_count", "–")))
        self.stat["Sifted key length"].configure(text=str(r.get("sifted_key_length", "–")))
        self.stat["Test sample size"].configure(text=str(r.get("test_sample_size", "–")))
        self.stat["Matching bits"].configure(text=str(r.get("matching_bits", "–")))
        self.stat["Mismatching bits"].configure(text=str(r.get("mismatches", "–")))
        self.stat["QBER"].configure(text=f"{qber:.2f}%", text_color=theme.EMERALD if passed else theme.RED)
        self.stat["Threshold"].configure(text=f"{thr:.2f}%")
        self.stat["Key material left"].configure(text=f"{r.get('remaining_key_bits', 0)} bits")
        if insufficient:
            self.decision_label.configure(text="Not enough data", text_color=theme.AMBER)
            self.decision_badge.update_kind("INSUFFICIENT DATA", "warning")
        elif passed:
            self.decision_label.configure(text="Security Check Passed", text_color=theme.EMERALD)
            self.decision_badge.update_kind("PASS", "success")
        else:
            self.decision_label.configure(text="Potential Eavesdropping Detected", text_color=theme.RED)
            self.decision_badge.update_kind("BLOCKED", "blocked")
        self.caption.configure(text=f"QBER {qber:.2f}% vs threshold {thr:.2f}% → "
                                    f"{'PASS' if passed else 'POSSIBLE EAVESDROPPING'}. Results come from the simulated measurements.")
        rows = []
        for row in (r.get("table") or [])[: self.table_rows]:
            rows.append({"position": row["position"], "alice_bit": row["alice_bit"], "alice_basis": row["alice_basis"],
                         "bob_basis": row["bob_basis"], "bob_result": row["bob_result"],
                         "kept": "Kept" if row["kept"] else "Discarded", "kept_kind": "success" if row["kept"] else "pending"})
        self.table.set_rows(rows)
        self.table_note.configure(text=f"Showing the first {len(rows)} of {r.get('bit_count', 0)} transmitted qubits "
                                       f"(bases '+' = rectilinear, 'x' = diagonal). Only positions with matching bases are kept.")
        self.redraw()
        if self._done_cb:
            cb, self._done_cb = self._done_cb, None
            cb()
