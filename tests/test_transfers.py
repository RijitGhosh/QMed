import io
import json
import random

import pytest

from client.encryption import decrypt_received, encrypt_for_recipient, establish_key
from common import crypto
from tests.conftest import PASSWORD, login, register


def send(client, headers, sender, recipient, plaintext=b"Fictional medical report\n" * 20, name="report.txt", eve=False, seed=1):
    kx = establish_key(1024 if not eve else 2048, eve, rng=random.Random(seed))
    if not kx.usable:
        return None, kx
    ct, meta = encrypt_for_recipient(plaintext, name, sender["user"]["id"], recipient["user"]["id"],
                                     recipient["public_key"], kx, "Please review")
    r = client.post("/api/transfers", headers=headers,
                    data={"metadata": json.dumps(meta), "file": (io.BytesIO(ct), "x.bin")},
                    content_type="multipart/form-data")
    return r, kx


def test_full_flow_one_client_logout_login(client, two_users):
    a, ha, b, hb = two_users
    plain = b"Demo patient report. Fictional only.\n" * 30
    r, _ = send(client, ha, a, b, plain)
    assert r.status_code == 201
    ref = r.get_json()["data"]["transfer"]["id"]
    assert ref.startswith("QMED-")
    client.post("/api/auth/logout", headers=ha)                       # sender logs out
    b2, hb2 = login(client, "bob_pat")                                # recipient logs in (new token)
    inbox = client.get("/api/transfers/inbox", headers=hb2).get_json()["data"]["transfers"]
    assert [t["id"] for t in inbox] == [ref]
    ct = client.get(f"/api/transfers/{ref}/download", headers=hb2).data
    assert plain not in ct
    key_info = client.get(f"/api/transfers/{ref}/key", headers=hb2).get_json()["data"]
    priv = crypto.unprotect_private_key(b2["encrypted_private_key"], PASSWORD)
    out, sha = decrypt_received(ct, key_info, priv)
    assert out == plain
    rep = client.post(f"/api/transfers/{ref}/decrypt", headers=hb2, json={"success": True, "recovered_sha256": sha})
    t = rep.get_json()["data"]["transfer"]
    assert t["status"] == "DECRYPTED" and t["integrity_status"] == "VERIFIED"


def test_server_never_stores_plaintext(client, two_users, app):
    a, ha, b, _ = two_users
    marker = b"TOP-SECRET-MARKER-12345 " * 10
    r, _ = send(client, ha, a, b, marker)
    assert r.status_code == 201
    for f in (app.config["QMED_SETTINGS"].storage_dir / "transfers").iterdir():
        assert marker[:20] not in f.read_bytes()


def test_unrelated_user_cannot_access(client, two_users):
    a, ha, b, hb = two_users
    register(client, "mallory", "Other")
    _, hm = login(client, "mallory")
    ref = send(client, ha, a, b)[0].get_json()["data"]["transfer"]["id"]
    assert client.get(f"/api/transfers/{ref}", headers=ha).status_code == 200      # sender
    assert client.get(f"/api/transfers/{ref}", headers=hb).status_code == 200      # recipient
    for path in (f"/api/transfers/{ref}", f"/api/transfers/{ref}/download", f"/api/transfers/{ref}/key"):
        assert client.get(path, headers=hm).status_code == 403
    # sender cannot fetch the recipient-only key/ciphertext either
    assert client.get(f"/api/transfers/{ref}/key", headers=ha).status_code == 403
    assert client.get("/api/transfers/inbox", headers=hm).get_json()["data"]["transfers"] == []
    assert client.get("/api/transfers/QMED-2026-9999", headers=hm).status_code == 404
    assert client.get("/api/transfers/..%2Fetc", headers=hm).status_code in (400, 404)
    assert client.get("/api/transfers/not-an-id", headers=hm).status_code == 400


def test_eve_blocks_transfer_and_is_recorded(client, two_users):
    a, ha, b, hb = two_users
    kx_result, kx = send(client, ha, a, b, eve=True, seed=7)
    assert kx_result is None and not kx.usable
    meta = {"recipient_id": b["user"]["id"], "original_filename": "r.txt", "file_size": 10,
            "original_sha256": "0" * 64, "bb84": kx.report()}
    r = client.post("/api/transfers/blocked", json=meta, headers=ha)
    assert r.status_code == 201 and r.get_json()["data"]["transfer"]["status"] == "BLOCKED"
    assert client.get("/api/transfers/inbox", headers=hb).get_json()["data"]["transfers"] == []
    sent = client.get("/api/transfers/sent", headers=ha).get_json()["data"]["transfers"]
    assert sent[0]["status"] == "BLOCKED"
    actions = [e["action"] for e in client.get("/api/activity", headers=ha).get_json()["data"]["events"]]
    assert "EAVESDROPPING_DETECTED" in actions and "TRANSFER_BLOCKED" in actions


def test_server_rejects_forged_pass_report(client, two_users):
    a, ha, b, _ = two_users
    bad = {"bit_count": 512, "sifted_key_length": 256, "test_sample_size": 64, "mismatches": 16, "qber": 0.25,
           "threshold": 0.11, "eve_enabled": True, "decision": "PASS", "key_confirmed": True}
    meta = {"recipient_id": b["user"]["id"], "original_filename": "r.txt", "file_size": 4,
            "original_sha256": "a" * 64, "nonce": "0" * 24, "key_id": "0" * 16, "encryption_algorithm": "AES-256-GCM",
            "key_envelope": {}, "bb84": bad}
    r = client.post("/api/transfers", headers=ha, data={"metadata": json.dumps(meta), "file": (io.BytesIO(b"x" * 20), "f")},
                    content_type="multipart/form-data")
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "SECURITY_CHECK_FAILED"


def test_file_validation(client, two_users):
    a, ha, b, _ = two_users
    plain_ext = send(client, ha, a, b, name="malware.exe")[0]
    assert plain_ext.status_code == 422 and plain_ext.get_json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    big = send(client, ha, a, b, plaintext=b"x" * 300_000)[0]
    assert big.status_code in (413, 422)
    self_send = send(client, ha, a, a)[0]
    assert self_send.status_code == 422


def test_path_traversal_filename_is_metadata_only(client, two_users, app):
    a, ha, b, _ = two_users
    r, _ = send(client, ha, a, b, name="../../evil.txt")
    assert r.status_code == 201 and r.get_json()["data"]["transfer"]["original_filename"] == "evil.txt"
    stored = list((app.config["QMED_SETTINGS"].storage_dir / "transfers").iterdir())
    assert len(stored) == 1 and stored[0].name.endswith(".qmed") and len(stored[0].stem) == 32


def test_file_storage_rejects_traversal(app):
    from server.errors import ApiError
    with pytest.raises(ApiError):
        app.extensions["qmed_storage"].read("../../etc/passwd")


def test_integrity_failure_recorded(client, two_users):
    a, ha, b, hb = two_users
    ref = send(client, ha, a, b)[0].get_json()["data"]["transfer"]["id"]
    r = client.post(f"/api/transfers/{ref}/decrypt", headers=hb, json={"success": True, "recovered_sha256": "f" * 64})
    assert r.get_json()["data"]["transfer"]["integrity_status"] == "FAILED"
