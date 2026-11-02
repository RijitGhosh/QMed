"""Shared helpers: audit logging, serialisation, transfer access control."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from flask import g, request

from common.validation import TRANSFER_REF_RE, clean_text

from .database import get_db
from .errors import ApiError
from .models import ActivityLog, Transfer, User

# Transfer statuses
PENDING, SECURITY_FAILED, ENCRYPTED, SENT = "PENDING", "SECURITY_CHECK_FAILED", "ENCRYPTED", "SENT"
DELIVERED, DECRYPTED, FAILED, BLOCKED = "DELIVERED", "DECRYPTED", "FAILED", "BLOCKED"
HIDDEN_FROM_RECIPIENT = (PENDING, SECURITY_FAILED, BLOCKED)
COMPLETED_STATES = (SENT, DELIVERED, DECRYPTED)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def log_activity(action: str, status: str = "SUCCESS", description: str = "",
                 transfer_ref: Optional[str] = None, user_id: Optional[int] = None) -> None:
    """Append an audit event. Never pass secrets/plaintext in `description`."""
    uid = user_id if user_id is not None else (g.user.id if "user" in g else None)
    get_db().add(ActivityLog(user_id=uid, action=action, status=status, transfer_id=transfer_ref,
                             description=clean_text(description, 300),
                             source_ip=request.remote_addr if request else None))


def user_public(u: User, with_keys: bool = False) -> Dict[str, Any]:
    data = {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role}
    if with_keys:
        data["public_key"] = u.public_key
    return data


def user_private(u: User) -> Dict[str, Any]:
    data = user_public(u)
    data.update(email=u.email, department=u.department, phone=u.phone,
                created_at=iso(u.created_at), last_login=iso(u.last_login))
    return data


def transfer_dict(t: Transfer) -> Dict[str, Any]:
    """Transfer metadata. Never includes stored file name, key envelope or any key."""
    return {
        "id": t.public_id, "sender": user_public(t.sender), "recipient": user_public(t.recipient),
        "original_filename": t.original_filename, "file_size": t.file_size,
        "original_sha256": t.original_sha256, "encryption_algorithm": t.encryption_algorithm,
        "key_id": t.key_id, "status": t.status, "integrity_status": t.integrity_status,
        "qber": t.qber, "qber_threshold": t.qber_threshold, "eve_enabled": t.eve_enabled,
        "bb84_status": t.bb84_status, "message": t.message,
        "created_at": iso(t.created_at), "updated_at": iso(t.updated_at),
    }


def get_transfer(ref: str, *, as_recipient: bool = False) -> Transfer:
    """Load a transfer the current user is authorised to see (404 hides existence)."""
    if not TRANSFER_REF_RE.match(ref or ""):
        raise ApiError(400, "INVALID_ID", "Invalid transfer identifier.")
    t = get_db().query(Transfer).filter_by(public_id=ref).first()
    uid = g.user.id
    allowed = t is not None and (t.recipient_id == uid if as_recipient else uid in (t.sender_id, t.recipient_id))
    if allowed and t.recipient_id == uid and t.status in HIDDEN_FROM_RECIPIENT:
        allowed = False
    if not allowed:
        if t is not None:
            raise ApiError(403, "FORBIDDEN", "You are not authorised to access this transfer.")
        raise ApiError(404, "NOT_FOUND", "Transfer not found.")
    return t


def json_body() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "INVALID_JSON", "Request body must be a valid JSON object.")
    return data
