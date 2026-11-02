"""Token sessions: random tokens, only HMAC hashes stored server-side."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

from flask import current_app, g, request

from .database import get_db
from .errors import ApiError
from .models import AuthSession, User, utcnow

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def hash_token(token: str) -> str:
    secret = current_app.config["QMED_SECRET"].encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


def create_session(user: User) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(hours=current_app.config["QMED_SETTINGS"].session_hours)
    get_db().add(AuthSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires))
    return token, expires


def _bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
    token = header[7:].strip()
    if not _TOKEN_RE.match(token):
        raise ApiError(401, "INVALID_TOKEN", "Invalid authentication token.")
    return token


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        db = get_db()
        sess = db.query(AuthSession).filter_by(token_hash=hash_token(token)).first()
        if not sess or sess.revoked or sess.expires_at < utcnow():
            raise ApiError(401, "SESSION_EXPIRED", "Your session is invalid or has expired. Please sign in again.")
        if not sess.user.is_active:
            raise ApiError(403, "ACCOUNT_DISABLED", "This account is disabled.")
        g.user, g.auth_session = sess.user, sess
        return view(*args, **kwargs)
    return wrapper
