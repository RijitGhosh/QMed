"""Encrypted document transfers. The server only ever sees ciphertext + a wrapped key."""
from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from flask import Blueprint, Response, current_app, g, request
from sqlalchemy import or_

from common.bb84 import DECISION_EAVESDROPPING, DECISION_INSUFFICIENT, DECISION_PASS
from common.crypto import ENCRYPTION_ALGORITHM, GCM_TAG_SIZE, KEY_WRAP_ALGORITHM
from common.validation import clean_text, file_extension, is_hex, safe_filename, MAX_MESSAGE_LEN

from ..auth import login_required
from ..database import get_db
from ..errors import ApiError, ok
from ..models import BB84Session, Transfer, User
from ..services import (BLOCKED, COMPLETED_STATES, DECRYPTED, DELIVERED, FAILED, HIDDEN_FROM_RECIPIENT,
                        SECURITY_FAILED, SENT, get_transfer, json_body, log_activity, transfer_dict)

bp = Blueprint("transfers", __name__, url_prefix="/api/transfers")
BB84_INT_FIELDS = ("bit_count", "sifted_key_length", "test_sample_size", "mismatches")


def _int(value: Any, name: str, lo: int = 0, hi: int = 10 ** 9) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ApiError(422, "VALIDATION_ERROR", f"Invalid value for {name}.")
    return value


def _validate_common(meta: Dict[str, Any]) -> Tuple[User, str, Dict[str, Any]]:
    """Validate recipient, filename and BB84 report shared by upload and blocked routes."""
    settings = current_app.config["QMED_SETTINGS"]
    recipient = get_db().get(User, _int(meta.get("recipient_id"), "recipient_id", 1))
    if not recipient or not recipient.is_active:
        raise ApiError(404, "RECIPIENT_NOT_FOUND", "The selected recipient does not exist.")
    if recipient.id == g.user.id and not settings.allow_self_send:
        raise ApiError(422, "VALIDATION_ERROR", "You cannot send a document to yourself.")
    filename = safe_filename(str(meta.get("original_filename") or ""))
    if not filename:
        raise ApiError(422, "VALIDATION_ERROR", "A file name is required.")
    if file_extension(filename) not in settings.allowed_extensions:
        raise ApiError(422, "UNSUPPORTED_FILE_TYPE",
                       "Unsupported file type. Allowed: " + ", ".join(settings.allowed_extensions) + ".")
    b = meta.get("bb84")
    if not isinstance(b, dict):
        raise ApiError(422, "VALIDATION_ERROR", "BB84 session report is required.")
    rep = {k: _int(b.get(k), k) for k in BB84_INT_FIELDS}
    if rep["mismatches"] > rep["test_sample_size"] or rep["test_sample_size"] > rep["sifted_key_length"]:
        raise ApiError(422, "VALIDATION_ERROR", "Inconsistent BB84 report.")
    try:
        rep["qber"], rep["threshold"] = float(b.get("qber")), float(b.get("threshold"))
    except (TypeError, ValueError):
        raise ApiError(422, "VALIDATION_ERROR", "Invalid BB84 numbers.")
    expected = rep["mismatches"] / rep["test_sample_size"] if rep["test_sample_size"] else 0.0
    if abs(expected - rep["qber"]) > 0.001 or not 0 < rep["threshold"] <= 0.5:
        raise ApiError(422, "VALIDATION_ERROR", "BB84 QBER does not match the reported measurements.")
    rep["eve_enabled"], rep["key_confirmed"] = bool(b.get("eve_enabled")), bool(b.get("key_confirmed"))
    return recipient, filename, rep


def _verdict(rep: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return (transfer_status_if_bad or '', bb84_status, message)."""
    server_thr = current_app.config["QMED_SETTINGS"].qber_threshold
    if rep["threshold"] > server_thr + 1e-9:
        return BLOCKED, "BLOCKED_THRESHOLD_TOO_LOOSE", "The reported threshold is looser than the server policy."
    if rep["test_sample_size"] == 0:
        return SECURITY_FAILED, "INSUFFICIENT_KEY_MATERIAL", "Not enough BB84 data to estimate QBER."
    if rep["qber"] > rep["threshold"]:
        return BLOCKED, "BLOCKED_POSSIBLE_EAVESDROPPING", "Possible eavesdropping detected (QBER above threshold)."
    if not rep["key_confirmed"]:
        return SECURITY_FAILED, "FAILED_KEY_CONFIRMATION", "Key confirmation failed; transfer aborted."
    return "", "PASSED", "Security check passed."


def _new_transfer(meta, recipient, filename, rep, status, bb84_status, **extra) -> Transfer:
    db = get_db()
    t = Transfer(sender_id=g.user.id, recipient_id=recipient.id, original_filename=filename,
                 file_size=_int(meta.get("file_size"), "file_size", 0, current_app.config["QMED_SETTINGS"].max_file_bytes),
                 original_sha256=meta.get("original_sha256") if is_hex(meta.get("original_sha256"), 64) else None,
                 status=status, qber=rep["qber"], qber_threshold=rep["threshold"], eve_enabled=rep["eve_enabled"],
                 bb84_status=bb84_status, message=clean_text(meta.get("message"), MAX_MESSAGE_LEN) or None, **extra)
    db.add(t)
    db.flush()
    t.public_id = f"QMED-{t.created_at.year}-{t.id:04d}"
    db.add(BB84Session(transfer_id=t.id, initiator_id=g.user.id, receiver_id=recipient.id,
                       bit_count=rep["bit_count"], sifted_key_length=rep["sifted_key_length"],
                       test_sample_size=rep["test_sample_size"], mismatches=rep["mismatches"], qber=rep["qber"],
                       threshold=rep["threshold"], eve_enabled=rep["eve_enabled"],
                       decision=DECISION_PASS if bb84_status == "PASSED" else
                       (DECISION_INSUFFICIENT if rep["test_sample_size"] == 0 else DECISION_EAVESDROPPING),
                       key_confirmed=rep["key_confirmed"]))
    return t


def _record_block(meta, recipient, filename, rep, status, bb84_status, message):
    t = _new_transfer(meta, recipient, filename, rep, status, bb84_status)
    action = "EAVESDROPPING_DETECTED" if status == BLOCKED else "BB84_COMPLETED"
    log_activity(action, "WARNING", message, t.public_id)
    log_activity("TRANSFER_BLOCKED", "BLOCKED", "Transfer stopped; no document was uploaded.", t.public_id)
    get_db().commit()
    return t


@bp.post("")
@login_required
def create_transfer():
    settings = current_app.config["QMED_SETTINGS"]
    try:
        meta = json.loads(request.form.get("metadata", ""))
        assert isinstance(meta, dict)
    except (ValueError, AssertionError):
        raise ApiError(400, "INVALID_JSON", "Transfer metadata must be a valid JSON object.")
    recipient, filename, rep = _validate_common(meta)
    bad_status, bb84_status, message = _verdict(rep)
    if bad_status:
        t = _record_block(meta, recipient, filename, rep, bad_status, bb84_status, message)
        raise ApiError(422, "SECURITY_CHECK_FAILED", message + f" Transfer {t.public_id} was blocked.")
    upload = request.files.get("file")
    if upload is None:
        raise ApiError(422, "VALIDATION_ERROR", "Encrypted file part is required.")
    data = upload.read()
    size = _int(meta.get("file_size"), "file_size", 0)
    if size > settings.max_file_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", f"File exceeds the {settings.max_file_bytes // (1024 * 1024)} MB limit.")
    if len(data) != size + GCM_TAG_SIZE:
        raise ApiError(422, "VALIDATION_ERROR", "Ciphertext length does not match the declared file size.")
    env = meta.get("key_envelope")
    if (meta.get("encryption_algorithm") != ENCRYPTION_ALGORITHM or not is_hex(meta.get("nonce"), 24)
            or not is_hex(meta.get("key_id"), 16) or not is_hex(meta.get("original_sha256"), 64)
            or not isinstance(env, dict) or env.get("alg") != KEY_WRAP_ALGORITHM
            or not all(is_hex(env.get(k)) for k in ("eph_pub", "nonce", "ct"))):
        raise ApiError(422, "VALIDATION_ERROR", "Encryption metadata is missing or malformed.")
    stored = current_app.extensions["qmed_storage"].save(data)
    t = _new_transfer(meta, recipient, filename, rep, SENT, "PASSED", stored_filename=stored,
                      encryption_algorithm=ENCRYPTION_ALGORITHM, nonce=meta["nonce"], key_id=meta["key_id"],
                      key_envelope=json.dumps(env))
    log_activity("BB84_COMPLETED", "SUCCESS", f"QBER {rep['qber'] * 100:.2f}% (pass).", t.public_id)
    log_activity("FILE_ENCRYPTED", "SUCCESS", "Document encrypted on the sender's device.", t.public_id)
    log_activity("FILE_SENT", "SUCCESS", f"Sent to {recipient.username}.", t.public_id)
    get_db().commit()
    return ok({"transfer": transfer_dict(t)}, 201)


@bp.post("/blocked")
@login_required
def report_blocked():
    """Client-side abort notice: records a blocked attempt (no file is ever uploaded)."""
    meta = json_body()
    recipient, filename, rep = _validate_common(meta)
    status, bb84_status, message = _verdict(rep)
    if not status:  # nothing actually wrong -> refuse to create noise
        raise ApiError(422, "VALIDATION_ERROR", "The reported BB84 session did not fail.")
    t = _record_block(meta, recipient, filename, rep, status, bb84_status, message)
    return ok({"transfer": transfer_dict(t)}, 201)


@bp.get("/inbox")
@login_required
def inbox():
    rows = (get_db().query(Transfer).filter(Transfer.recipient_id == g.user.id,
                                            Transfer.status.notin_(HIDDEN_FROM_RECIPIENT))
            .order_by(Transfer.created_at.desc()).limit(500).all())
    return ok({"transfers": [transfer_dict(t) for t in rows]})


@bp.get("/sent")
@login_required
def sent():
    rows = (get_db().query(Transfer).filter(Transfer.sender_id == g.user.id)
            .order_by(Transfer.created_at.desc()).limit(500).all())
    return ok({"transfers": [transfer_dict(t) for t in rows]})


@bp.get("/<ref>")
@login_required
def detail(ref: str):
    return ok({"transfer": transfer_dict(get_transfer(ref))})


@bp.get("/<ref>/download")
@login_required
def download(ref: str):
    t = get_transfer(ref, as_recipient=True)
    data = current_app.extensions["qmed_storage"].read(t.stored_filename or "")
    if t.status == SENT:
        t.status = DELIVERED
    log_activity("FILE_RECEIVED", "SUCCESS", "Encrypted document retrieved by recipient.", t.public_id)
    get_db().commit()
    return Response(data, mimetype="application/octet-stream")


@bp.get("/<ref>/key")
@login_required
def key_material(ref: str):
    """Wrapped key for the recipient only. The server cannot unwrap it (prototype: it still relays it)."""
    t = get_transfer(ref, as_recipient=True)
    return ok({"key_envelope": json.loads(t.key_envelope or "{}"), "nonce": t.nonce,
               "sender_id": t.sender_id, "recipient_id": t.recipient_id, "original_sha256": t.original_sha256})


@bp.post("/<ref>/decrypt")
@login_required
def report_decryption(ref: str):
    """Recipient reports the outcome of the local decryption; server records/compares hashes."""
    t, body = get_transfer(ref, as_recipient=True), json_body()
    if body.get("success") is True:
        recovered = str(body.get("recovered_sha256") or "")
        if recovered == t.original_sha256:
            t.status, t.integrity_status = DECRYPTED, "VERIFIED"
            log_activity("FILE_DECRYPTED", "SUCCESS", "Document decrypted by recipient.", t.public_id)
            log_activity("INTEGRITY_VERIFIED", "SUCCESS", "Recovered SHA-256 matches original.", t.public_id)
        else:
            t.status, t.integrity_status = FAILED, "FAILED"
            log_activity("INTEGRITY_FAILED", "FAILURE", "Recovered SHA-256 differs from original.", t.public_id)
    else:
        t.status, t.integrity_status = FAILED, "FAILED"
        log_activity("DECRYPTION_FAILED", "FAILURE", clean_text(body.get("reason") or "Decryption failed.", 200),
                     t.public_id)
    get_db().commit()
    return ok({"transfer": transfer_dict(t)})
