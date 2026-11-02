import random

import pytest

from client.encryption import decrypt_received, encrypt_for_recipient, establish_key, new_account_keys
from common import crypto
from common.crypto import DecryptionError


def _kx(seed=1):
    kx = establish_key(1024, False, rng=random.Random(seed))
    assert kx.usable
    return kx


def test_key_derivation_deterministic_and_confirmed():
    r = establish_key(1024, False, rng=random.Random(4))
    assert r.key_confirmed and len(r.key) == 32


def test_eve_blocks_key():
    kx = establish_key(2048, True, rng=random.Random(5))
    assert not kx.usable and kx.key is None


def test_insufficient_material_rejected():
    assert not establish_key(128, False, rng=random.Random(6)).usable


def test_roundtrip_and_ciphertext_differs():
    priv, pub = crypto.generate_keypair()
    plain = b"Fictional report " * 50
    ct, meta = encrypt_for_recipient(plain, "r.txt", 1, 2, pub.hex(), _kx())
    assert ct != plain and plain[:16] not in ct
    info = {"key_envelope": meta["key_envelope"], "nonce": meta["nonce"], "sender_id": 1, "recipient_id": 2,
            "original_sha256": meta["original_sha256"]}
    out, sha = decrypt_received(ct, info, priv)
    assert out == plain and sha == meta["original_sha256"] == crypto.sha256_hex(plain)


def test_corrupted_ciphertext_and_wrong_key_fail():
    priv, pub = crypto.generate_keypair()
    ct, meta = encrypt_for_recipient(b"hello world" * 10, "r.txt", 1, 2, pub.hex(), _kx(2))
    info = {"key_envelope": meta["key_envelope"], "nonce": meta["nonce"], "sender_id": 1, "recipient_id": 2,
            "original_sha256": meta["original_sha256"]}
    bad = bytearray(ct); bad[0] ^= 1
    with pytest.raises(DecryptionError):
        decrypt_received(bytes(bad), info, priv)
    other_priv, _ = crypto.generate_keypair()
    with pytest.raises(DecryptionError):
        decrypt_received(ct, info, other_priv)
    with pytest.raises(DecryptionError):  # tampered metadata (AAD) is detected
        decrypt_received(ct, {**info, "sender_id": 9}, priv)


def test_private_key_protection():
    pub, blob = new_account_keys("Str0ngPass")
    assert crypto.unprotect_private_key(blob, "Str0ngPass")
    with pytest.raises(DecryptionError):
        crypto.unprotect_private_key(blob, "wrong")
