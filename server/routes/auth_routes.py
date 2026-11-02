"""Registration, login, logout and password change."""
from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, current_app, g, request
from sqlalchemy import func, or_

from common.validation import (check_password, clean_text, is_hex, validate_email, validate_role,
                               validate_username, MAX_NAME_LEN)

from ..auth import create_session, login_required
from ..database import get_db
from ..errors import ApiError, ok
from ..models import AuthSession, User, utcnow
from ..security import hash_password, verify_password
from ..services import json_body, log_activity, user_private

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _validate_keystore(body: dict) -> tuple[str, str]:
    pub, blob = body.get("public_key"), body.get("encrypted_private_key")
    if not is_hex(pub, 64) or not isinstance(blob, dict) or not {"salt", "nonce", "ct"} <= set(blob):
        raise ApiError(422, "VALIDATION_ERROR", "A valid encryption key pair is required.")
    return pub, json.dumps(blob)


@bp.post("/register")
def register():
    body, settings = json_body(), current_app.config["QMED_SETTINGS"]
    full_name = clean_text(body.get("full_name"), MAX_NAME_LEN)
    username = clean_text(body.get("username"), 32)
    email = clean_text(body.get("email"), 254).lower()
    password, role = str(body.get("password") or ""), str(body.get("role") or "")
    errors = [e for e in (("Full name is required." if not full_name else None),
                          validate_username(username), validate_email(email), validate_role(role)) if e]
    errors += check_password(password, settings.password_policy)
    if errors:
        raise ApiError(422, "VALIDATION_ERROR", " ".join(errors))
    pub, blob = _validate_keystore(body)
    db = get_db()
    if db.query(User).filter(func.lower(User.username) == username.lower()).first():
        raise ApiError(409, "USERNAME_TAKEN", "That username is already registered.")
    if db.query(User).filter(User.email == email).first():
        raise ApiError(409, "EMAIL_TAKEN", "That email is already registered.")
    pw_hash, salt = hash_password(password)
    user = User(full_name=full_name, username=username, email=email, password_hash=pw_hash,
                password_salt=salt, role=role, department=clean_text(body.get("department"), 80) or None,
                phone=clean_text(body.get("phone"), 32) or None, public_key=pub, encrypted_private_key=blob)
    db.add(user)
    db.flush()
    log_activity("REGISTER", "SUCCESS", "Account created.", user_id=user.id)
    db.commit()
    return ok({"user": user_private(user)}, 201)


@bp.post("/login")
def login():
    body, throttle = json_body(), current_app.extensions["qmed_throttle"]
    ident, password = clean_text(body.get("identifier"), 254), str(body.get("password") or "")
    if not ident or not password:
        raise ApiError(422, "VALIDATION_ERROR", "Username/email and password are required.")
    key = ident.lower()
    if throttle.blocked(key):
        raise ApiError(429, "TOO_MANY_ATTEMPTS", "Too many failed sign-in attempts. Try again in a few minutes.")
    db = get_db()
    user = db.query(User).filter(or_(func.lower(User.username) == key, User.email == key)).first()
    if not user or not verify_password(password, user.password_hash, user.password_salt):
        throttle.record_failure(key)
        log_activity("LOGIN_FAILURE", "FAILURE", "Invalid credentials.", user_id=user.id if user else None)
        db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid username or password.")
    if not user.is_active:
        raise ApiError(403, "ACCOUNT_DISABLED", "This account is disabled.")
    throttle.reset(key)
    user.last_login = utcnow()
    token, expires = create_session(user)
    log_activity("LOGIN_SUCCESS", "SUCCESS", "Signed in.", user_id=user.id)
    db.commit()
    return ok({"token": token, "expires_at": expires.isoformat() + "Z", "user": user_private(user),
               "public_key": user.public_key, "encrypted_private_key": json.loads(user.encrypted_private_key)})


@bp.post("/logout")
@login_required
def logout():
    g.auth_session.revoked = True
    log_activity("LOGOUT", "SUCCESS", "Signed out.")
    get_db().commit()
    return ok({"message": "Signed out."})


@bp.post("/change-password")
@login_required
def change_password():
    body, settings = json_body(), current_app.config["QMED_SETTINGS"]
    current, new = str(body.get("current_password") or ""), str(body.get("new_password") or "")
    user = g.user
    if not verify_password(current, user.password_hash, user.password_salt):
        log_activity("PASSWORD_CHANGE", "FAILURE", "Wrong current password.")
        get_db().commit()
        raise ApiError(403, "INVALID_CREDENTIALS", "The current password is incorrect.")
    problems = check_password(new, settings.password_policy)
    if problems:
        raise ApiError(422, "VALIDATION_ERROR", " ".join(problems))
    _, blob = _validate_keystore({"public_key": user.public_key, "encrypted_private_key": body.get("encrypted_private_key")})
    user.password_hash, user.password_salt = hash_password(new)
    user.encrypted_private_key = blob
    for s in get_db().query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.id != g.auth_session.id):
        s.revoked = True  # other sessions are signed out
    log_activity("PASSWORD_CHANGE", "SUCCESS", "Password changed.")
    get_db().commit()
    return ok({"message": "Password updated."})
