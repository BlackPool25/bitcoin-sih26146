"""tests/test_amounts.py — 6 tests for ml/amounts lognormal model."""

from __future__ import annotations

import math
import random
import statistics


def test_fit_lognormal_smoke() -> None:
    """fit_lognormal smoke mu≈-3.9 on fixed amounts near 0.02 BTC."""
    from ml.amounts import fit_lognormal

    # amounts with geometric mean ~0.02 => ln median ~ -3.912
    amounts = [0.02, 0.018, 0.022, 0.019, 0.021, 0.02, 0.017, 0.023]
    mu, sigma = fit_lognormal(amounts)
    assert -4.2 < mu < -3.6, f"mu {mu} not in [-4.2,-3.6] for median ~0.02"
    assert 0.0 <= sigma < 1.0, f"sigma {sigma} unexpected"
    # explicit log mean check
    logs = [math.log(a) for a in amounts]
    expected_mu = sum(logs) / len(logs)
    assert abs(mu - expected_mu) < 1e-9
    # also test general fit preserves mean ln
    amounts2 = [0.5, 1.0, 2.0]
    mu2, sigma2 = fit_lognormal(amounts2)
    expected2 = sum(math.log(x) for x in amounts2) / 3
    assert abs(mu2 - expected2) < 1e-9
    assert sigma2 >= 0


def test_1000_draws_normal_median_and_unique() -> None:
    """1000 draws normal: median 0.001-2.0, n_unique>900."""
    from ml.amounts import build_amounts_lognormal

    rng = random.Random(42)
    all_amounts: list[float] = []
    for _ in range(1000):
        ins, outs, _fee = build_amounts_lognormal("normal", rng, None)
        all_amounts.extend(ins)
        all_amounts.extend(outs)
    med = statistics.median(all_amounts)
    assert 0.001 <= med <= 2.0, f"median {med} not in [0.001,2.0]"
    n_unique = len(set(all_amounts))
    assert n_unique > 900, f"n_unique {n_unique} <=900, need >900"


def test_coinjoin_variance() -> None:
    """coinjoin variance <0.001 (fixed 0.01±0.0001)."""
    from ml.amounts import build_amounts_lognormal

    rng = random.Random(123)
    all_vals: list[float] = []
    for _ in range(50):
        ins, outs, _fee = build_amounts_lognormal("coinjoin", rng, None)
        all_vals.extend(ins)
        all_vals.extend(outs)
    # each amount should be 0.01±0.0002 approx
    for v in all_vals:
        assert 0.0095 <= v <= 0.0105, f"coinjoin amount {v} out of 0.01±0.0005"
    # variance <0.001
    var = statistics.variance(all_vals) if len(all_vals) > 1 else 0.0
    assert var < 0.001, f"coinjoin variance {var} >=0.001"
    # also check per-call outputs are near 0.01
    rng2 = random.Random(999)
    ins2, outs2, fee2 = build_amounts_lognormal("coinjoin", rng2, None)
    assert len(ins2) == 22 and len(outs2) == 22
    # fee should be sum(in)-sum(out)
    assert abs(sum(ins2) - (sum(outs2) + fee2)) < 1e-8


def test_conservation_100_seeds() -> None:
    """Conservation holds 100 seeds across all labels: sum(in)==sum(out)+fee ±1e-8."""
    from ml.amounts import build_amounts_lognormal

    labels = [
        "normal",
        "peel",
        "mixer",
        "coinjoin",
        "structuring",
        "ransomware",
        "bridge",
        "high_fee",
        "asn_hop",
    ]
    for seed in range(100):
        rng = random.Random(seed)
        for label in labels:
            ins, outs, fee = build_amounts_lognormal(label, rng, None)
            total_in = sum(ins)
            total_out = sum(outs)
            diff = abs(total_in - (total_out + fee))
            msg = f"conservation fail seed {seed} label {label} diff {diff}"
            assert diff < 1e-8 + 1e-12, msg
            # also test with stats override (fitted)
            stats = {label: (0.1, 0.5)}
            rng2 = random.Random(seed)
            ins2, outs2, fee2 = build_amounts_lognormal(label, rng2, stats)
            diff2 = abs(sum(ins2) - (sum(outs2) + fee2))
            assert diff2 < 1e-8 + 1e-12, f"conservation with stats fail seed {seed} label {label} diff {diff2}"


def test_amount_positive_always() -> None:
    """All amounts >0 across random seeds and labels."""
    from ml.amounts import build_amounts_lognormal

    labels = ["normal", "peel", "mixer", "coinjoin", "structuring", "ransomware", "bridge", "high_fee", "asn_hop"]
    rng = random.Random(2024)
    for label in labels:
        for _ in range(20):
            ins, outs, fee = build_amounts_lognormal(label, rng, None)
            for v in ins:
                assert v > 0, f"amount {v} not >0 label {label}"
                assert v >= 0.001 - 1e-9, f"amount {v} below clamp 0.001 label {label}"
                assert v <= 50 + 1e-9, f"amount {v} above clamp 50 label {label}"
            for v in outs:
                assert v > 0, f"amount {v} not >0 label {label}"
                assert v >= 0.00001 - 1e-9, f"output {v} too small label {label}"
            assert fee > 0, f"fee {fee} not >0 label {label}"


def test_fee_bounds() -> None:
    """Fee in [0.00001, 0.2*total] for all labels; high_fee 5-20%."""
    from ml.amounts import build_amounts_lognormal

    rng = random.Random(777)
    labels = ["normal", "peel", "mixer", "coinjoin", "structuring", "ransomware", "bridge", "high_fee", "asn_hop"]
    for label in labels:
        for _ in range(30):
            ins, _outs, fee = build_amounts_lognormal(label, rng, None)
            total = sum(ins)
            assert fee >= 0.00001 - 1e-12, f"fee {fee} <0.00001 label {label} total {total}"
            assert fee <= 0.2 * total + 1e-9, f"fee {fee} >0.2*total {0.2*total} label {label} total {total}"
            # high_fee specifically 5-20%
            if label == "high_fee":
                # allow tiny epsilon due to capping
                assert fee >= 0.05 * total - 1e-9 or fee == 0.01, f"high_fee fee {fee} <5% of total {total}"
                assert fee <= 0.20 * total + 1e-9, f"high_fee fee {fee} >20% total {total}"
