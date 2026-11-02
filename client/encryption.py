"""Client-side cryptographic workflows (no GUI imports; fully unit-testable).

The plaintext document is encrypted on the sender's machine and decrypted on the
recipient's machine.  The server only stores ciphertext plus a wrapped key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from common import crypto
from common.bb84 import BB84Result, DECISION_PASS, DEFAULT_QBER_THRESHOLD, run_bb84


@dataclass
class KeyExchange:
    """Result of the simulated BB84 exchange plus derived (in-memory only) key."""

    result: BB84Result
    key: Optional[bytes]
    key_confirmed: bool

    @property
    def usable(self) -> bool:
        return self.result.key_material_ok and self.key_confirmed and self.key is not None

    def report(self) -> Dict[str, Any]:
        """Statistics sent to the server. Contains NO key material."""
        r = self.result
        return {"bit_count": r.n_bits, "sifted_key_length": r.sifted_length,
                "test_sample_size": r.test_sample_size, "mismatches": r.mismatches, "qber": r.qber,
                "threshold": r.threshold, "eve_enabled": r.eve_enabled, "decision": r.decision,
                "key_confirmed": self.key_confirmed}


def establish_key(n_bits: int, eve_enabled: bool, threshold: float = DEFAULT_QBER_THRESHOLD,
                  channel_noise: float = 0.0, rng=None) -> KeyExchange:
    """Run BB84, then (only if it passes) derive both parties' keys with HKDF and confirm them."""
    result = run_bb84(n_bits, eve_enabled, threshold, channel_noise, rng=rng)
    if result.decision != DECISION_PASS or not result.key_material_ok:
        return KeyExchange(result, None, False)
    alice_key = crypto.derive_file_key(result.alice_key_bits, result.session_id)
    bob_key = crypto.derive_file_key(result.bob_key_bits, result.session_id)
    confirmed = crypto.confirm_key_agreement(alice_key, bob_key)
    return KeyExchange(result, alice_key if confirmed else None, confirmed)


def encrypt_for_recipient(plaintext: bytes, filename: str, sender_id: int, recipient_id: int,
                          recipient_public_hex: str, kx: KeyExchange, message: str = "") -> Tuple[bytes, Dict[str, Any]]:
    """Encrypt with AES-256-GCM using the BB84-derived key and wrap that key for the recipient."""
    if not kx.usable:
        raise crypto.CryptoError("No confirmed BB84 key is available.")
    sha = crypto.sha256_hex(plaintext)
    aad = crypto.transfer_aad(sender_id, recipient_id, sha)
    nonce, ciphertext = crypto.encrypt_bytes(kx.key, plaintext, aad)
    envelope = crypto.wrap_file_key(kx.key, bytes.fromhex(recipient_public_hex), aad)
    meta = {"recipient_id": recipient_id, "original_filename": filename, "file_size": len(plaintext),
            "original_sha256": sha, "encryption_algorithm": crypto.ENCRYPTION_ALGORITHM,
            "nonce": nonce.hex(), "key_id": crypto.key_id(kx.key), "key_envelope": envelope,
            "message": message, "bb84": kx.report()}
    return ciphertext, meta


def decrypt_received(ciphertext: bytes, key_info: Dict[str, Any], private_raw: bytes) -> Tuple[bytes, str]:
    """Unwrap the file key, decrypt (verifies the GCM tag) and return (plaintext, recovered_sha256)."""
    sha = key_info["original_sha256"]
    aad = crypto.transfer_aad(key_info["sender_id"], key_info["recipient_id"], sha)
    file_key = crypto.unwrap_file_key(key_info["key_envelope"], private_raw, aad)
    plaintext = crypto.decrypt_bytes(file_key, bytes.fromhex(key_info["nonce"]), ciphertext, aad)
    return plaintext, crypto.sha256_hex(plaintext)


def new_account_keys(password: str) -> Tuple[str, Dict[str, str]]:
    """Generate an X25519 key pair; return (public_hex, password-protected private key blob)."""
    private_raw, public_raw = crypto.generate_keypair()
    return public_raw.hex(), crypto.protect_private_key(private_raw, password)
