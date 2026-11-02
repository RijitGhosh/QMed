"""Sent files: everything the signed-in user has sent (including blocked attempts)."""
from __future__ import annotations

from typing import Any, Dict

from common.validation import human_size
from .. import theme
from ..components.tables import fmt_time
from .transfer_list import TransferListScreen


class SentScreen(TransferListScreen):
    title, subtitle, direction = "Sent Files", "Documents you sent, with their security and delivery status.", "sent"
    empty_title, empty_text, empty_kind = "No documents have been sent yet.", "Use Send Document to securely share a file.", "sent"

    def columns(self):
        return [{"key": "recipient", "title": "Recipient", "weight": 3, "min": 100, "max": 18},
                {"key": "role", "title": "Role", "weight": 1, "min": 70},
                {"key": "file", "title": "File Name", "weight": 3, "min": 110, "max": 18},
                {"key": "date", "title": "Sent", "weight": 2, "min": 125},
                {"key": "size", "title": "Size", "weight": 1, "min": 70},
                {"key": "qber", "title": "QBER", "weight": 1, "min": 80},
                {"key": "enc", "title": "Encryption", "weight": 2, "min": 100},
                {"key": "status", "title": "Status", "weight": 2, "min": 120, "kind": "badge"}]

    def fetch(self):
        return self.app.api.sent()

    def row(self, t: Dict[str, Any]) -> Dict[str, Any]:
        return {"recipient": t["recipient"]["full_name"], "role": t["recipient"]["role"], "file": t["original_filename"],
                "date": fmt_time(t["created_at"]), "size": human_size(t["file_size"]),
                "qber": "–" if t["qber"] is None else f"{t['qber'] * 100:.2f}%", "enc": t.get("encryption_algorithm") or "–",
                "status": theme.status_label(t["status"]), "status_kind": theme.STATUS_KIND.get(t["status"], "info")}
