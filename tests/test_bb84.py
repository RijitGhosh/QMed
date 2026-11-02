import random

import pytest

from common.bb84 import (DECISION_EAVESDROPPING, DECISION_PASS, compute_qber, evaluate_decision, run_bb84)


def test_eve_off_has_no_errors():
    for seed in range(5):
        r = run_bb84(1024, eve_enabled=False, rng=random.Random(seed))
        assert r.mismatches == 0 and r.qber == 0.0 and r.decision == DECISION_PASS
        assert r.alice_key_bits == r.bob_key_bits


def test_eve_on_introduces_about_25_percent_errors():
    rates = [run_bb84(2048, eve_enabled=True, rng=random.Random(s)).qber for s in range(6)]
    assert 0.15 < sum(rates) / len(rates) < 0.35
    assert all(run_bb84(2048, True, rng=random.Random(s)).decision == DECISION_EAVESDROPPING for s in range(6))


def test_sifted_length_about_half():
    r = run_bb84(2048, rng=random.Random(1))
    assert 900 < r.sifted_length < 1150


def test_qber_calculation_and_threshold():
    assert compute_qber(3, 12) == pytest.approx(0.25)
    assert evaluate_decision(0.10, 0.11) == DECISION_PASS
    assert evaluate_decision(0.11, 0.11) == DECISION_PASS
    assert evaluate_decision(0.1101, 0.11) == DECISION_EAVESDROPPING
    with pytest.raises(ValueError):
        compute_qber(0, 0)


def test_test_bits_removed_from_key():
    r = run_bb84(1024, rng=random.Random(2))
    assert r.remaining_key_bits == r.sifted_length - r.test_sample_size


def test_public_dict_has_no_key_bits():
    d = run_bb84(512, rng=random.Random(3)).to_public_dict()
    assert "alice_key_bits" not in d and "bob_key_bits" not in d
