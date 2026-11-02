"""Flask application factory for the QMed backend."""
from __future__ import annotations

import logging
import time
from typing import Optional

from flask import Flask, g, request
from werkzeug.exceptions import HTTPException

from .config import Settings, load_settings
from .database import Database, close_db
from .errors import ApiError, error_response
from .file_storage import FileStorage
from .logging_config import setup_logging
from .security import LoginThrottle

_HTTP_CODES = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND",
               405: "METHOD_NOT_ALLOWED", 413: "FILE_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE"}


def create_app(settings: Optional[Settings] = None) -> Flask:
    """Create the app; first run creates directories, database file and schema."""
    settings = settings or load_settings()
    settings.ensure_directories()
    setup_logging(settings.log_dir)
    log, err_log = logging.getLogger("qmed.backend"), logging.getLogger("qmed.app")

    app = Flask(__name__)
    app.config["QMED_SETTINGS"] = settings
    app.config["QMED_SECRET"] = settings.resolve_secret()
    app.config["MAX_CONTENT_LENGTH"] = settings.max_file_bytes + 256 * 1024
    app.config["TESTING"] = settings.testing

    db = Database(settings.database_url)
    db.create_schema()
    app.extensions["qmed_db"] = db
    app.extensions["qmed_storage"] = FileStorage(settings.storage_dir)
    app.extensions["qmed_throttle"] = LoginThrottle()
    app.teardown_appcontext(close_db)

    from .routes import activity_routes, auth_routes, bb84_routes, transfer_routes, user_routes
    for module in (auth_routes, user_routes, transfer_routes, bb84_routes, activity_routes):
        app.register_blueprint(module.bp)

    @app.before_request
    def _start_timer():
        g.t0 = time.perf_counter()

    @app.after_request
    def _log_request(resp):
        if request.path != "/api/health":  # never logs headers, bodies or tokens
            log.info("%s %s -> %s (%.0f ms)", request.method, request.path, resp.status_code,
                     (time.perf_counter() - g.get("t0", time.perf_counter())) * 1000)
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return error_response(e.status, e.code, e.message)

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        code = e.code or 500
        return error_response(code, _HTTP_CODES.get(code, "HTTP_ERROR"), e.description or "Request failed.")

    @app.errorhandler(Exception)
    def _unexpected(e: Exception):
        err_log.exception("Unhandled server error")  # stack trace goes to error.log only
        return error_response(500, "INTERNAL_ERROR", "An unexpected server error occurred.")

    return app
