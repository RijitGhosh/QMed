"""Structured logging: application.log, backend.log, error.log (no secrets logged)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FMT = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")


def _file_handler(path: Path, level: int) -> logging.Handler:
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(_FMT)
    return handler


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    app_log, backend_log = logging.getLogger("qmed.app"), logging.getLogger("qmed.backend")
    if getattr(app_log, "_qmed_ready", False):
        return
    app_log.setLevel(logging.INFO)
    backend_log.setLevel(logging.INFO)
    app_log.addHandler(_file_handler(log_dir / "application.log", logging.INFO))
    backend_log.addHandler(_file_handler(log_dir / "backend.log", logging.INFO))
    err = _file_handler(log_dir / "error.log", logging.ERROR)
    for lg in (app_log, backend_log):
        lg.addHandler(err)
    console = logging.StreamHandler()
    console.setFormatter(_FMT)
    backend_log.addHandler(console)
    app_log._qmed_ready = True  # type: ignore[attr-defined]
