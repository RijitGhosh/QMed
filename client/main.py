"""QMed desktop client entry point:  python -m client.main"""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from typing import Any, Callable, List, Optional

import customtkinter as ctk

from common.crypto import CryptoError
from . import theme
from .api_client import ApiClient, ApiError
from .components.notifications import Toaster
from .config import APP_NAME, APP_TAGLINE, HEALTH_CHECK_SECONDS, SETTINGS_DIR, LocalSettings
from .security import KeyVault

log = logging.getLogger("qmed.client")


def _setup_logging() -> None:
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=str(SETTINGS_DIR / "client.log"), level=logging.INFO,
                            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    except OSError:
        pass


class QMedApp(ctk.CTk):
    def __init__(self) -> None:
        self.settings = LocalSettings()
        ctk.set_appearance_mode(self.settings.get("theme"))
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=theme.BG)
        self.title(f"{APP_NAME} – {APP_TAGLINE}")
        w, h = 1280, 800
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(w, sw - 40), min(h, sh - 80)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(1100, 700)

        self.api = ApiClient(self.settings.get("server_url"))
        self.vault = KeyVault()
        self.user: Optional[dict] = None
        self.server_config: dict = {"qber_threshold": 0.11, "max_file_bytes": 10 * 1024 * 1024,
                                    "allowed_extensions": ["txt", "pdf", "docx", "csv", "png", "jpg", "jpeg"],
                                    "password_policy": {}, "session_hours": 8}
        self.connected: Optional[bool] = None
        self.theme_listeners: List[Callable[[], None]] = []
        self.connection_listeners: List[Callable[[bool], None]] = []
        self.shell = None
        self._current: Optional[ctk.CTkFrame] = None
        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.toaster = Toaster(self)
        self.after(40, self._poll)
        self.after(200, self.check_connection)
        self.show_public("welcome")

    # ------------------------------------------------------------ threading
    def call_soon(self, fn: Callable[[], None]) -> None:
        """Schedule `fn` on the UI thread (safe to call from worker threads)."""
        self._queue.put(fn)

    def run_async(self, work: Callable[[], Any], on_success: Optional[Callable[[Any], None]] = None,
                  on_error: Optional[Callable[[Exception], None]] = None) -> None:
        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - reported to the UI
                self.call_soon(lambda e=exc: (on_error or self.handle_error)(e))
            else:
                if on_success:
                    self.call_soon(lambda r=result: on_success(r))
        threading.Thread(target=runner, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn()
                except tk.TclError:
                    pass  # widget was destroyed while the task was running
                except Exception:  # noqa: BLE001
                    log.exception("UI callback failed")
        except queue.Empty:
            pass
        self.after(40, self._poll)

    # --------------------------------------------------------------- errors
    def handle_error(self, exc: Exception) -> None:
        if isinstance(exc, ApiError):
            if exc.code in ("SESSION_EXPIRED", "INVALID_TOKEN", "UNAUTHORIZED") and self.user:
                self.logout(expired=True)
                return
            if exc.code == "CONNECTION_ERROR":
                self.set_connected(False)
            self.notify("warning" if exc.code in ("SECURITY_CHECK_FAILED", "TOO_MANY_ATTEMPTS") else "error", exc.message)
        elif isinstance(exc, CryptoError):
            self.notify("error", str(exc))
        else:
            log.exception("Unexpected client error", exc_info=exc)
            self.notify("error", "Something went wrong. Please try again.")

    def notify(self, kind: str, message: str) -> None:
        self.toaster.show(kind, message)

    # ----------------------------------------------------------- connection
    def set_connected(self, ok: bool) -> None:
        if ok != self.connected:
            self.connected = ok
            for cb in list(self.connection_listeners):
                try:
                    cb(ok)
                except tk.TclError:
                    self.connection_listeners.remove(cb)

    def check_connection(self, now: bool = False) -> None:
        def work():
            self.api.health()
            return self.api.config()

        def ok(cfg):
            self.server_config.update(cfg)
            self.set_connected(True)

        self.run_async(work, ok, lambda _e: self.set_connected(False))
        if not now:
            self.after(HEALTH_CHECK_SECONDS * 1000, self.check_connection)

    # ------------------------------------------------------------- screens
    def _swap(self, frame: ctk.CTkFrame) -> None:
        if self._current is not None:
            self._current.destroy()
        self._current = frame
        frame.pack(fill="both", expand=True)

    def show_public(self, name: str, **kw) -> None:
        from .screens.about import PublicAbout
        from .screens.login import LoginScreen
        from .screens.signup import SignupScreen
        from .screens.welcome import WelcomeScreen
        self.shell = None
        screens = {"welcome": WelcomeScreen, "login": LoginScreen, "signup": SignupScreen, "about": PublicAbout}
        self._swap(screens[name](self.container, self, **kw))

    def on_login(self, data: dict) -> None:
        self.user = data["user"]
        from .shell import Shell
        self.shell = Shell(self.container, self)
        self._swap(self.shell)
        self.shell.navigate("dashboard")
        self.notify("success", f"Welcome back, {self.user['full_name']}.")

    def logout(self, expired: bool = False) -> None:
        """Clear all client-side authenticated state immediately, then revoke the token server-side."""
        token, url = self.api.token, self.api.base_url
        self.api.token, self.user = None, None
        self.vault.clear()

        def revoke():
            tmp = ApiClient(url)
            tmp.token = token
            try:
                tmp.logout()
            except ApiError:
                pass
        if token:
            self.run_async(revoke)
        self.show_public("login")
        self.notify("warning" if expired else "info",
                    "Your session expired. Please sign in again." if expired else "You have been signed out.")

    # ---------------------------------------------------------------- theme
    def set_theme(self, mode: str) -> None:
        self.settings.set(theme=mode)
        ctk.set_appearance_mode(mode)
        for cb in list(self.theme_listeners):
            try:
                cb()
            except tk.TclError:
                self.theme_listeners.remove(cb)
        if self.shell:
            self.shell.header.refresh_theme_icon()

    def toggle_theme(self) -> None:
        self.set_theme("light" if self.settings.get("theme") == "dark" else "dark")
        if self.shell is None and hasattr(self._current, "refresh_theme_icon"):
            self._current.refresh_theme_icon()

    def effective_threshold(self) -> float:
        return min(float(self.settings.get("qber_threshold")), float(self.server_config.get("qber_threshold", 0.11)))


def main() -> None:
    _setup_logging()
    QMedApp().mainloop()


if __name__ == "__main__":
    main()
