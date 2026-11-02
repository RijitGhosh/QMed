"""Start the QMed server:  python -m server.run_server  (or python run_server.py)."""
from __future__ import annotations

import socket

from .app import create_app
from .config import APP_VERSION, load_settings


def lan_ip() -> str:
    """Best-effort LAN address (no packets are sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    print("=" * 58)
    print(f"  QMed Server v{APP_VERSION}  -  educational BB84 simulation")
    print("=" * 58)
    print("  Server running on:")
    print(f"    Local:   http://127.0.0.1:{settings.port}")
    if settings.host in ("0.0.0.0", "::"):
        print(f"    Network: http://{lan_ip()}:{settings.port}   (trusted LAN only, plain HTTP)")
    print(f"  Database: {settings.database_url}")
    print("  Press Ctrl+C to stop.\n")
    app.run(host=settings.host, port=settings.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
