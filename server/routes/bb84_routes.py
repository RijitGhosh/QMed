"""Server-side BB84 lab endpoint (statistics only; no key material is returned or stored)."""
from __future__ import annotations

from flask import Blueprint, g

from common.bb84 import ALLOWED_BIT_COUNTS, DECISION_EAVESDROPPING, run_bb84

from ..auth import login_required
from ..database import get_db
from ..errors import ApiError, ok
from ..models import BB84Session
from ..services import json_body, log_activity

bp = Blueprint("bb84", __name__, url_prefix="/api/bb84")


@bp.post("/simulate")
@login_required
def simulate():
    body = json_body()
    bits, eve = body.get("bits", 512), bool(body.get("eve", False))
    try:
        threshold = float(body.get("threshold", 0.11))
        noise = float(body.get("channel_noise", 0.0))
    except (TypeError, ValueError):
        raise ApiError(422, "VALIDATION_ERROR", "Threshold and noise must be numbers.")
    if bits not in ALLOWED_BIT_COUNTS or isinstance(bits, bool):
        raise ApiError(422, "VALIDATION_ERROR", f"Bit count must be one of {list(ALLOWED_BIT_COUNTS)}.")
    if not 0.01 <= threshold <= 0.5 or not 0.0 <= noise < 0.2:
        raise ApiError(422, "VALIDATION_ERROR", "Threshold must be 1%-50% and channel noise below 20%.")
    log_activity("BB84_STARTED", "SUCCESS", f"Lab run: {bits} bits, Eve {'ON' if eve else 'OFF'}.")
    res = run_bb84(bits, eve, threshold, noise)
    get_db().add(BB84Session(initiator_id=g.user.id, bit_count=bits, sifted_key_length=res.sifted_length,
                             test_sample_size=res.test_sample_size, mismatches=res.mismatches, qber=res.qber,
                             threshold=threshold, eve_enabled=eve, decision=res.decision))
    if res.decision == DECISION_EAVESDROPPING:
        log_activity("EAVESDROPPING_DETECTED", "WARNING", f"Lab QBER {res.qber * 100:.2f}% above threshold.")
    else:
        log_activity("BB84_COMPLETED", "SUCCESS", f"Lab QBER {res.qber * 100:.2f}%.")
    get_db().commit()
    return ok({"result": res.to_public_dict(table_limit=32)})
