"""Educational software simulation of the BB84 quantum key distribution protocol.

IMPORTANT: no physical quantum system is involved.  A "qubit" is represented as
a (bit, basis) pair and measurement follows the textbook rule:

* measuring in the SAME basis as the preparation returns the encoded bit;
* measuring in the OTHER basis returns a uniformly random bit (the state is
  disturbed).

Every number reported (sifted length, mismatches, QBER) is computed from the
simulated measurements - nothing is hard-coded or randomly "faked".
"""
from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

BASIS_RECTILINEAR = 0  # "+" basis: |0>, |1>
BASIS_DIAGONAL = 1     # "x" basis: |+>, |->
BASIS_SYMBOL = {BASIS_RECTILINEAR: "+", BASIS_DIAGONAL: "x"}

DEFAULT_QBER_THRESHOLD = 0.11   # educational default (not a universal policy)
TEST_FRACTION = 0.25            # share of sifted key disclosed for QBER estimation
MIN_TEST_SAMPLE = 16
MIN_KEY_BITS = 128              # minimum secret bits required before running the KDF
ALLOWED_BIT_COUNTS = (128, 256, 512, 1024, 2048, 4096)
DEFAULT_BIT_COUNT = 512

DECISION_PASS = "PASS"
DECISION_EAVESDROPPING = "POSSIBLE_EAVESDROPPING"
DECISION_INSUFFICIENT = "INSUFFICIENT_DATA"

_STATE_LABEL = {(0, 0): "|0>", (1, 0): "|1>", (0, 1): "|+>", (1, 1): "|->"}


@dataclass(frozen=True)
class Qubit:
    """Educational qubit: an encoded bit plus the basis it was prepared in."""

    bit: int
    basis: int

    @property
    def label(self) -> str:
        return _STATE_LABEL[(self.bit, self.basis)]

    def measure(self, basis: int, rng: random.Random) -> int:
        """Measure in ``basis``: deterministic if the basis matches, else random."""
        return self.bit if basis == self.basis else rng.getrandbits(1)


@dataclass
class BB84Result:
    """Outcome of one simulated BB84 run (secret bits stay in-process)."""

    session_id: str
    n_bits: int
    eve_enabled: bool
    threshold: float
    channel_noise: float
    sifted_length: int
    test_sample_size: int
    mismatches: int
    qber: float
    decision: str
    table: List[Dict[str, object]] = field(default_factory=list)
    alice_key_bits: List[int] = field(default_factory=list, repr=False)
    bob_key_bits: List[int] = field(default_factory=list, repr=False)

    @property
    def matching_bits(self) -> int:
        return self.test_sample_size - self.mismatches

    @property
    def remaining_key_bits(self) -> int:
        return len(self.alice_key_bits)

    @property
    def key_material_ok(self) -> bool:
        return self.decision == DECISION_PASS and self.remaining_key_bits >= MIN_KEY_BITS

    def to_public_dict(self, table_limit: int = 24) -> Dict[str, object]:
        """Statistics safe to store/transmit - never includes secret key bits."""
        return {
            "session_id": self.session_id,
            "bit_count": self.n_bits,
            "eve_enabled": self.eve_enabled,
            "threshold": self.threshold,
            "channel_noise": self.channel_noise,
            "sifted_key_length": self.sifted_length,
            "test_sample_size": self.test_sample_size,
            "matching_bits": self.matching_bits,
            "mismatches": self.mismatches,
            "qber": self.qber,
            "decision": self.decision,
            "remaining_key_bits": self.remaining_key_bits,
            "key_material_ok": self.key_material_ok,
            "table": self.table[:table_limit],
        }


def evaluate_decision(qber: float, threshold: float) -> str:
    """Security decision: PASS when QBER is at or below the configured threshold."""
    return DECISION_PASS if qber <= threshold else DECISION_EAVESDROPPING


def compute_qber(mismatches: int, sample_size: int) -> float:
    """QBER = mismatched sampled bits / total sampled bits."""
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    return mismatches / sample_size


def run_bb84(
    n_bits: int = DEFAULT_BIT_COUNT,
    eve_enabled: bool = False,
    threshold: float = DEFAULT_QBER_THRESHOLD,
    channel_noise: float = 0.0,
    rng: Optional[random.Random] = None,
    test_fraction: float = TEST_FRACTION,
    table_rows: int = 64,
) -> BB84Result:
    """Simulate BB84 between Alice and Bob, optionally with an intercept-resend Eve.

    Stages: (1) Alice bits, (2) Alice bases, (3) Bob bases, (4) transmission,
    (5) optional Eve, (6) basis comparison, (7) sifting, (8) QBER sampling,
    (9) decision.  Pass ``rng=random.Random(seed)`` for reproducible tests.
    """
    if n_bits < 8:
        raise ValueError("n_bits must be at least 8")
    if not 0.0 <= channel_noise < 0.5:
        raise ValueError("channel_noise must be in [0, 0.5)")
    rng = rng or random.SystemRandom()

    alice_bits = [rng.getrandbits(1) for _ in range(n_bits)]           # stage 1
    alice_bases = [rng.getrandbits(1) for _ in range(n_bits)]          # stage 2
    bob_bases = [rng.getrandbits(1) for _ in range(n_bits)]            # stage 3
    eve_bases = [rng.getrandbits(1) for _ in range(n_bits)] if eve_enabled else []

    bob_results: List[int] = []
    for i in range(n_bits):                                            # stage 4
        qubit = Qubit(alice_bits[i], alice_bases[i])
        if eve_enabled:                                                # stage 5
            eve_bit = qubit.measure(eve_bases[i], rng)
            qubit = Qubit(eve_bit, eve_bases[i])                       # resend
        if channel_noise and rng.random() < channel_noise:
            qubit = Qubit(qubit.bit ^ 1, qubit.basis)
        bob_results.append(qubit.measure(bob_bases[i], rng))

    kept = [i for i in range(n_bits) if alice_bases[i] == bob_bases[i]]  # stages 6-7
    alice_sifted = [alice_bits[i] for i in kept]
    bob_sifted = [bob_results[i] for i in kept]

    table = []
    for i in range(min(n_bits, table_rows)):
        table.append({
            "position": i + 1,
            "alice_bit": alice_bits[i],
            "alice_basis": BASIS_SYMBOL[alice_bases[i]],
            "eve_basis": BASIS_SYMBOL[eve_bases[i]] if eve_enabled else None,
            "bob_basis": BASIS_SYMBOL[bob_bases[i]],
            "bob_result": bob_results[i],
            "kept": alice_bases[i] == bob_bases[i],
        })

    session_id = secrets.token_hex(8)
    sifted_len = len(kept)
    if sifted_len < 2 * MIN_TEST_SAMPLE:
        return BB84Result(session_id, n_bits, eve_enabled, threshold, channel_noise,
                          sifted_len, 0, 0, 0.0, DECISION_INSUFFICIENT, table)

    sample_size = max(MIN_TEST_SAMPLE, round(sifted_len * test_fraction))   # stage 8
    sample_idx = set(rng.sample(range(sifted_len), sample_size))
    mismatches = sum(1 for i in sample_idx if alice_sifted[i] != bob_sifted[i])
    qber = compute_qber(mismatches, sample_size)
    decision = evaluate_decision(qber, threshold)                          # stage 9

    # Publicly disclosed test bits are discarded; the rest is shared key material.
    alice_key = [b for i, b in enumerate(alice_sifted) if i not in sample_idx]
    bob_key = [b for i, b in enumerate(bob_sifted) if i not in sample_idx]
    return BB84Result(session_id, n_bits, eve_enabled, threshold, channel_noise,
                      sifted_len, sample_size, mismatches, qber, decision, table,
                      alice_key, bob_key)


def bits_to_bytes(bits: Sequence[int]) -> bytes:
    """Pack a bit list (MSB first, zero padded) into bytes."""
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (7 - i % 8)
    return bytes(out)
