"""HTTP client for the QMed REST API (timeouts, friendly errors, no secrets in logs)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests

CONNECT_TIMEOUT, READ_TIMEOUT = 4, 30
CONNECTION_MESSAGE = "Unable to connect to QMed Server. Verify the server address and network connection."


class ApiError(Exception):
    """Error with a stable code and a message that is safe to show to users."""

    def __init__(self, code: str, message: str, status: int = 0):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self._http = requests.Session()

    def set_base_url(self, url: str) -> None:
        self.base_url = url.strip().rstrip("/")

    # ------------------------------------------------------------ plumbing
    def _request(self, method: str, path: str, *, auth: bool = True, raw: bool = False, **kwargs) -> Any:
        headers = {}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            resp = self._http.request(method, self.base_url + path, headers=headers,
                                      timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), **kwargs)
        except requests.exceptions.MissingSchema:
            raise ApiError("BAD_URL", "The server address must start with http:// or https://.")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.InvalidURL):
            raise ApiError("CONNECTION_ERROR", CONNECTION_MESSAGE)
        except requests.exceptions.RequestException:
            raise ApiError("NETWORK_ERROR", "A network error occurred. Please try again.")
        if resp.status_code < 400 and raw:
            return resp.content
        try:
            body = resp.json()
        except ValueError:
            raise ApiError("BAD_RESPONSE", "The server sent an unexpected response.", resp.status_code)
        if not body.get("success"):
            err = body.get("error") or {}
            raise ApiError(err.get("code", "ERROR"), err.get("message", "Request failed."), resp.status_code)
        return body.get("data", {})

    # ------------------------------------------------------------ public
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/health", auth=False)

    def config(self) -> Dict[str, Any]:
        return self._request("GET", "/api/config", auth=False)

    def register(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/auth/register", auth=False, json=payload)

    def login(self, identifier: str, password: str) -> Dict[str, Any]:
        data = self._request("POST", "/api/auth/login", auth=False,
                             json={"identifier": identifier, "password": password})
        self.token = data["token"]
        return data

    # --------------------------------------------------------- authenticated
    def logout(self) -> None:
        try:
            self._request("POST", "/api/auth/logout")
        finally:
            self.token = None

    def change_password(self, current: str, new: str, encrypted_private_key: Dict[str, str]) -> None:
        self._request("POST", "/api/auth/change-password", json={
            "current_password": current, "new_password": new, "encrypted_private_key": encrypted_private_key})

    def users(self, q: str = "") -> List[Dict[str, Any]]:
        return self._request("GET", "/api/users", params={"q": q})["users"]

    def profile(self) -> Dict[str, Any]:
        return self._request("GET", "/api/profile")["user"]

    def update_profile(self, **fields: Any) -> Dict[str, Any]:
        return self._request("PUT", "/api/profile", json=fields)["user"]

    def dashboard(self) -> Dict[str, Any]:
        return self._request("GET", "/api/dashboard")

    def activity(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/activity")["events"]

    def log_event(self, action: str, description: str = "") -> None:
        try:
            self._request("POST", "/api/activity", json={"action": action, "description": description})
        except ApiError:
            pass  # audit hints are best-effort

    def inbox(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/transfers/inbox")["transfers"]

    def sent(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/transfers/sent")["transfers"]

    def transfer(self, ref: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/transfers/{ref}")["transfer"]

    def upload_transfer(self, ciphertext: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/transfers", data={"metadata": json.dumps(metadata)},
                             files={"file": ("payload.bin", ciphertext, "application/octet-stream")})["transfer"]

    def report_blocked(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/transfers/blocked", json=metadata)["transfer"]

    def download(self, ref: str) -> bytes:
        return self._request("GET", f"/api/transfers/{ref}/download", raw=True)

    def key_material(self, ref: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/transfers/{ref}/key")

    def report_decryption(self, ref: str, success: bool, recovered_sha256: str = "", reason: str = "") -> Dict[str, Any]:
        return self._request("POST", f"/api/transfers/{ref}/decrypt", json={
            "success": success, "recovered_sha256": recovered_sha256, "reason": reason})["transfer"]

    def simulate_bb84(self, bits: int, eve: bool, threshold: float) -> Dict[str, Any]:
        return self._request("POST", "/api/bb84/simulate", json={"bits": bits, "eve": eve, "threshold": threshold})["result"]
