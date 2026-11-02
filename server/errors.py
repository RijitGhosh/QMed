"""Standard API error type and response helpers."""
from __future__ import annotations

from typing import Any, Optional

from flask import jsonify


class ApiError(Exception):
    """Raised anywhere in a request to produce a standard JSON error."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def ok(data: Optional[Any] = None, status: int = 200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def error_response(status: int, code: str, message: str):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status
