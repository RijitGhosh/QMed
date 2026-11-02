"""Cryptographic helpers built on the `cryptography` package (no custom algorithms).

Design (educational prototype):
  BB84 sifted key  --HKDF-SHA256-->  256-bit file key  --AES-256-GCM-->  ciphertext
  The file key is wrapped for the recipient with X25519 ECDH + HKDF + AES-GCM so the
  server only ever stores ciphertext and a wrapped key it cannot open.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Dict, Sequence, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .bb84 import MIN_KEY_BITS, bits_to_bytes

ENCRYPTION_ALGORITHM = "AES-256-GCM"
KEY_WRAP_ALGORITHM = "X25519+HKDF-SHA256+AES-256-GCM"
NONCE_SIZE = 12
GCM_TAG_SIZE = 16
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1


class CryptoError(Exception):
    """Base class for user-presentable cryptographic failures."""


class DecryptionError(CryptoError):
    """Authentication tag mismatch, wrong key, or corrupted ciphertext."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- BB84 -> key
def derive_file_key(key_bits: Sequence[int], session_id: str) -> bytes:
    """Derive a 256-bit key from BB84 key material with HKDF-SHA256."""
    if len(key_bits) < MIN_KEY_BITS:
        raise CryptoError("Not enough BB84 key material to derive a key.")
    return HKDF(
        algorithm=hashes.SHA256(), length=32,
        salt=hashlib.sha256(b"QMed-BB84-salt-v1|" + session_id.encode()).digest(),
        info=b"QMed file encryption key v1",
    ).derive(bits_to_bytes(key_bits))


def key_id(key: bytes) -> str:
    """Non-secret identifier for a key (HMAC of a constant label)."""
    return hmac.new(key, b"QMED-KEY-ID", hashlib.sha256).hexdigest()[:16]


def key_confirmation_tag(key: bytes, role: str) -> str:
    return hmac.new(key, b"QMED-KEY-CONFIRM|" + role.encode(), hashlib.sha256).hexdigest()


def confirm_key_agreement(alice_key: bytes, bob_key: bytes) -> bool:
    """Mutual HMAC key confirmation; the keys themselves are never compared/revealed."""
    a_ok = hmac.compare_digest(key_confirmation_tag(alice_key, "alice"),
                               key_confirmation_tag(bob_key, "alice"))
    b_ok = hmac.compare_digest(key_confirmation_tag(alice_key, "bob"),
                               key_confirmation_tag(bob_key, "bob"))
    return a_ok and b_ok


# ------------------------------------------------------------ file encryption
def transfer_aad(sender_id: int, recipient_id: int, sha256: str) -> bytes:
    """Associated data binding ciphertext to its sender, recipient and original hash."""
    return f"QMED|v1|{sender_id}|{recipient_id}|{sha256}".encode()


def encrypt_bytes(key: bytes, plaintext: bytes, aad: bytes) -> Tuple[bytes, bytes]:
    """AES-256-GCM encrypt. Returns (nonce, ciphertext||tag)."""
    nonce = os.urandom(NONCE_SIZE)
    return nonce, AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt_bytes(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except (InvalidTag, ValueError) as exc:
        raise DecryptionError("Authentication failed: wrong key or corrupted data.") from exc


# ------------------------------------------------- recipient key wrapping
def generate_keypair() -> Tuple[bytes, bytes]:
    """Return (private_raw, public_raw) for X25519."""
    priv = X25519PrivateKey.generate()
    return (
        priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                           serialization.NoEncryption()),
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
    )


def _wrap_kek(shared: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"QMed key wrap v1").derive(shared)


def wrap_file_key(file_key: bytes, recipient_public: bytes, aad: bytes) -> Dict[str, str]:
    eph = X25519PrivateKey.generate()
    shared = eph.exchange(X25519PublicKey.from_public_bytes(recipient_public))
    nonce = os.urandom(NONCE_SIZE)
    ct = AESGCM(_wrap_kek(shared)).encrypt(nonce, file_key, aad)
    eph_pub = eph.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"alg": KEY_WRAP_ALGORITHM, "eph_pub": eph_pub.hex(), "nonce": nonce.hex(), "ct": ct.hex()}


def unwrap_file_key(envelope: Dict[str, str], recipient_private: bytes, aad: bytes) -> bytes:
    try:
        priv = X25519PrivateKey.from_private_bytes(recipient_private)
        shared = priv.exchange(X25519PublicKey.from_public_bytes(bytes.fromhex(envelope["eph_pub"])))
        return AESGCM(_wrap_kek(shared)).decrypt(bytes.fromhex(envelope["nonce"]),
                                                 bytes.fromhex(envelope["ct"]), aad)
    except (InvalidTag, ValueError, KeyError) as exc:
        raise DecryptionError("Unable to unwrap the file key for this account.") from exc


# ------------------------------------- password-protected private key storage
def _scrypt(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(
        b"QMed-keystore|" + password.encode())


def protect_private_key(private_raw: bytes, password: str) -> Dict[str, str]:
    salt, nonce = os.urandom(16), os.urandom(NONCE_SIZE)
    ct = AESGCM(_scrypt(password, salt)).encrypt(nonce, private_raw, b"QMED-PRIVKEY-V1")
    return {"kdf": "scrypt", "salt": salt.hex(), "nonce": nonce.hex(), "ct": ct.hex()}


def unprotect_private_key(blob: Dict[str, str], password: str) -> bytes:
    try:
        key = _scrypt(password, bytes.fromhex(blob["salt"]))
        return AESGCM(key).decrypt(bytes.fromhex(blob["nonce"]), bytes.fromhex(blob["ct"]),
                                   b"QMED-PRIVKEY-V1")
    except (InvalidTag, ValueError, KeyError) as exc:
        raise DecryptionError("Unable to unlock your encryption key with this password.") from exc
