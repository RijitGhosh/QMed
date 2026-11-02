"""Activity log and dashboard statistics."""
from __future__ import annotations

from flask import Blueprint, g, request
from sqlalchemy import func

from common.bb84 import DECISION_EAVESDROPPING

from ..auth import login_required
from ..database import get_db
from ..errors import ApiError, ok
from ..models import ActivityLog, BB84Session, Transfer
from ..services import (COMPLETED_STATES, DELIVERED, HIDDEN_FROM_RECIPIENT, SENT, iso, json_body, log_activity)

bp = Blueprint("activity", __name__, url_prefix="/api")
CLIENT_EVENTS = {"FILE_SELECTED", "BB84_STARTED", "FILE_ENCRYPTED_LOCAL"}


def _activity_dict(a: ActivityLog) -> dict:
    return {"id": a.id, "timestamp": iso(a.timestamp), "user": a.user.username if a.user else "-",
            "action": a.action, "status": a.status, "transfer_id": a.transfer_id,
            "description": a.description, "source_ip": a.source_ip}


@bp.get("/activity")
@login_required
def activity():
    limit = min(max(request.args.get("limit", 200, type=int), 1), 500)
    rows = (get_db().query(ActivityLog).filter(ActivityLog.user_id == g.user.id)
            .order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc()).limit(limit).all())
    return ok({"events": [_activity_dict(a) for a in rows]})


@bp.post("/activity")
@login_required
def client_event():
    body = json_body()
    action = str(body.get("action") or "")
    if action not in CLIENT_EVENTS:
        raise ApiError(422, "VALIDATION_ERROR", "Unsupported activity event.")
    log_activity(action, "SUCCESS", str(body.get("description") or ""), body.get("transfer_id"))
    get_db().commit()
    return ok({})


@bp.get("/dashboard")
@login_required
def dashboard():
    db, uid = get_db(), g.user.id
    count = lambda q: q.scalar() or 0
    sent = count(db.query(func.count(Transfer.id)).filter(Transfer.sender_id == uid, Transfer.status.in_(COMPLETED_STATES + ("FAILED",))))
    received = count(db.query(func.count(Transfer.id)).filter(Transfer.recipient_id == uid, Transfer.status.notin_(HIDDEN_FROM_RECIPIENT)))
    successful = count(db.query(func.count(Transfer.id)).filter(
        (Transfer.sender_id == uid) | (Transfer.recipient_id == uid), Transfer.status.in_(COMPLETED_STATES)))
    checks = count(db.query(func.count(BB84Session.id)).filter(BB84Session.initiator_id == uid))
    threats = count(db.query(func.count(BB84Session.id)).filter(BB84Session.initiator_id == uid,
                                                                 BB84Session.decision == DECISION_EAVESDROPPING))
    pending = count(db.query(func.count(Transfer.id)).filter(Transfer.recipient_id == uid, Transfer.status.in_((SENT, DELIVERED))))
    recent = (db.query(ActivityLog).filter(ActivityLog.user_id == uid)
              .order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc()).limit(8).all())
    return ok({"total_sent": sent, "total_received": received, "successful_transfers": successful,
               "security_checks": checks, "threats_detected": threats, "pending_documents": pending,
               "recent_activity": [_activity_dict(a) for a in recent]})
