"""Inbox: documents addressed to the signed-in user."""
from __future__ import annotations

from typing import Any, Dict

from common.validation import human_size
from .. import theme
from ..components.tables import fmt_time
from .transfer_dialogs import DecryptDialog, TransferDetails
from .transfer_list import TransferListScreen


class InboxScreen(TransferListScreen):
    title, subtitle, direction = "Inbox", "Encrypted documents sent to you. Nothing is decrypted until you choose Decrypt.", "inbox"
    empty_title, empty_text, empty_kind = "Your inbox is empty", "Documents sent to you will appear here, encrypted.", "inbox"

    def columns(self):
        return [{"key": "sender", "title": "Sender", "weight": 3, "min": 100, "max": 18},
                {"key": "role", "title": "Role", "weight": 1, "min": 60},
                {"key": "file", "title": "File Name", "weight": 3, "min": 110, "max": 18},
                {"key": "date", "title": "Date", "weight": 2, "min": 125},
                {"key": "size", "title": "Size", "weight": 1, "min": 55},
                {"key": "security", "title": "Security", "weight": 2, "min": 105, "kind": "badge"},
                {"key": "status", "title": "Status", "weight": 2, "min": 100, "kind": "badge"},
                {"key": "actions", "title": "Actions", "weight": 3, "min": 150, "kind": "actions"}]

    def fetch(self):
        return self.app.api.inbox()

    def row(self, t: Dict[str, Any]) -> Dict[str, Any]:
        text, kind = self.security_cell(t)
        return {"sender": t["sender"]["full_name"], "role": t["sender"]["role"], "file": t["original_filename"],
                "date": fmt_time(t["created_at"]), "size": human_size(t["file_size"]), "security": text, "security_kind": kind,
                "status": {"SENT": "New"}.get(t["status"], theme.status_label(t["status"])), "status_kind": theme.STATUS_KIND.get(t["status"], "info"),
                "actions": [("Details", lambda t=t: self.details(t)), ("Decrypt", lambda t=t: self.decrypt(t))]}

    def details(self, t) -> None:
        TransferDetails(self.app, t, on_decrypt=self.decrypt)

    def decrypt(self, t) -> None:
        DecryptDialog(self.app, t, on_finished=self.load)
