"""User directory, profile, health and public config."""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, g, request
from sqlalchemy import or_

from common.validation import MAX_NAME_LEN, clean_text, validate_email

from ..auth import login_required
from ..config import APP_VERSION
from ..database import get_db
from ..errors import ApiError, ok
from ..models import User, utcnow
from ..services import json_body, log_activity, user_private, user_public

bp = Blueprint("users", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return ok({"status": "ok", "version": APP_VERSION, "time": utcnow().isoformat() + "Z"})


@bp.get("/config")
def public_config():
    return ok(current_app.config["QMED_SETTINGS"].public_config())


@bp.get("/users")
@login_required
def list_users():
    q = clean_text(request.args.get("q"), 40)
    query = get_db().query(User).filter(User.is_active.is_(True))
    if not current_app.config["QMED_SETTINGS"].allow_self_send:
        query = query.filter(User.id != g.user.id)
    if q:
        like = f"%{q.lower()}%"
        from sqlalchemy import func
        query = query.filter(or_(func.lower(User.username).like(like), func.lower(User.full_name).like(like)))
    users = query.order_by(User.full_name).limit(200).all()
    return ok({"users": [user_public(u, with_keys=True) for u in users]})


@bp.get("/profile")
@login_required
def get_profile():
    return ok({"user": user_private(g.user)})


@bp.put("/profile")
@login_required
def update_profile():
    body, user, db = json_body(), g.user, get_db()
    if "full_name" in body:
        name = clean_text(body["full_name"], MAX_NAME_LEN)
        if not name:
            raise ApiError(422, "VALIDATION_ERROR", "Full name cannot be empty.")
        user.full_name = name
    if "email" in body:
        email = clean_text(body["email"], 254).lower()
        problem = validate_email(email)
        if problem:
            raise ApiError(422, "VALIDATION_ERROR", problem)
        if db.query(User).filter(User.email == email, User.id != user.id).first():
            raise ApiError(409, "EMAIL_TAKEN", "That email is already registered.")
        user.email = email
    if "department" in body:
        user.department = clean_text(body["department"], 80) or None
    if "phone" in body:
        user.phone = clean_text(body["phone"], 32) or None
    log_activity("PROFILE_UPDATED", "SUCCESS", "Profile updated.")
    db.commit()
    return ok({"user": user_private(user)})
