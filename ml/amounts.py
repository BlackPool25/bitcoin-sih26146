"""ml/amounts — lognormal per-label amounts with conservation (WITS 2024 Table 2)."""

from __future__ import annotations

import math
import random  # noqa: TC003

_CLAMP_MIN = 0.001
_CLAMP_MAX = 50.0
_FEE_MAX_FRAC = 0.20
_FEE_MIN_ABS = 0.00001
_COINJOIN_N = 22
_COINJOIN_CENTER = 0.01
_COINJOIN_JITTER = 0.0001

_PRIORS: dict[str, tuple[float, float] | None] = {
    "normal": (-0.8, 1.2),
    "peel": (0.5, 0.6),
    "mixer": (0.2, 1.0),
    "coinjoin": None,
    "structuring": (-1.0, 0.8),
    "ransomware": (1.1, 0.9),
    "bridge": (0.7, 0.85),
    "high_fee": (-0.3, 1.0),
    "asn_hop": (-0.6, 1.1),
}
LABEL_PRIORS: dict[str, tuple[float, float] | None] = dict(_PRIORS)


def fit_lognormal(amounts: list[float]) -> tuple[float, float]:
    """Fit mu, sigma via mean(ln) and std(ln)."""
    if not amounts:
        return (0.0, 0.0)
    pos = [a for a in amounts if a > 0]
    if not pos:
        return (0.0, 0.0)
    if len(pos) == 1:
        return (math.log(pos[0]), 0.0)
    logs = [math.log(a) for a in pos]
    n = len(logs)
    mu = sum(logs) / n
    var = sum((x - mu) ** 2 for x in logs) / n
    return (float(mu), float(math.sqrt(var) if var > 0 else 0.0))


def _clamp(v: float) -> float:
    return _CLAMP_MIN if v < _CLAMP_MIN else _CLAMP_MAX if v > _CLAMP_MAX else v


def _sample(rng: random.Random, mu: float, sigma: float) -> float:
    return round(float(_clamp(rng.lognormvariate(mu, sigma))), 8)


def _get_mu_sigma(
    label: str,
    stats: dict[str, tuple[float, float]] | dict[int, tuple[float, float]] | None,
) -> tuple[float, float] | None:
    if stats is not None and label in stats:  # type: ignore[operator]
        v = stats[label]  # type: ignore[index]
        return (float(v[0]), float(v[1]))  # type: ignore[index]
    p = _PRIORS.get(label)
    if p is not None:
        return p
    return _PRIORS["normal"]


def split_amount(total: float, n: int, rng: random.Random) -> list[float]:
    """Preserve generate_synthetic split_amount (round8, diff fix, >0, last adjust)."""
    if n == 1:
        return [round(total, 8)]
    weights = [rng.random() + 0.1 for _ in range(n)]
    s = sum(weights)
    raw = [w / s * total for w in weights]
    rounded = [round(x, 8) for x in raw]
    diff = round(total - sum(rounded), 8)
    rounded[-1] = round(rounded[-1] + diff, 8)
    if rounded[-1] <= 0:
        rounded[-1] = round(total - sum(rounded[:-1]), 8)
    for i, v in enumerate(rounded):
        if v <= 0:
            rounded[i] = 0.00001
    rounded[-1] = round(total - sum(rounded[:-1]), 8)
    return rounded


def _fee_capped(total_in: float, fee: float) -> float:
    max_fee = round(total_in * _FEE_MAX_FRAC, 8)
    if fee > max_fee:
        fee = max_fee
    if fee < _FEE_MIN_ABS:
        fee = _FEE_MIN_ABS
    if total_in - fee <= 0:
        fee = round(total_in * 0.01, 8)
        if fee < _FEE_MIN_ABS:
            fee = _FEE_MIN_ABS
        if fee > max_fee:
            fee = max_fee
    if fee > round(total_in * _FEE_MAX_FRAC, 8):
        fee = round(total_in * _FEE_MAX_FRAC, 8)
    return round(float(fee), 8)


def build_amounts_lognormal(
    label: str,
    rng: random.Random,
    stats: dict[str, tuple[float, float]]
    | dict[int, tuple[float, float]]
    | None = None,
) -> tuple[list[float], list[float], float]:
    """Build (inputs, outputs, fee) lognormal per label, conservation ±1e-8."""
    if label == "coinjoin":
        n = _COINJOIN_N
        outs: list[float] = []
        for _ in range(n):
            v = round(_COINJOIN_CENTER + rng.uniform(-_COINJOIN_JITTER, _COINJOIN_JITTER), 8)
            if v <= 0:
                v = 0.0099
            outs.append(round(max(_CLAMP_MIN, min(_CLAMP_MAX, v)), 8))
        ins = [round(max(_CLAMP_MIN, min(_CLAMP_MAX, o + 0.0001)), 8) for o in outs]
        fee = round(sum(ins) - sum(outs), 8)
        max_fee = round(sum(ins) * _FEE_MAX_FRAC, 8)
        if fee < _FEE_MIN_ABS:
            fee = _FEE_MIN_ABS
            ins[-1] = round(sum(outs) + fee - sum(ins[:-1]), 8)
        if fee > max_fee:
            fee = max_fee
            ins[-1] = round(sum(outs) + fee - sum(ins[:-1]), 8)
        ins[-1] = round(sum(outs) + fee - sum(ins[:-1]), 8)
        if ins[-1] <= 0:
            ins[-1] = 0.00001
            fee = round(sum(ins) - sum(outs), 8)
        return ins, outs, float(fee)

    mu_sigma = _get_mu_sigma(label, stats)
    assert mu_sigma is not None
    mu, sigma = mu_sigma

    if label == "mixer":
        if rng.random() < 0.5:
            n_in, n_out = rng.randint(5, 10), rng.randint(1, 2)
        else:
            n_in, n_out = rng.randint(1, 2), rng.randint(5, 10)
        ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
        tot = round(sum(ins), 8)
        fee = _fee_capped(tot, round(rng.uniform(0.0001, 0.002), 8))
        return ins, split_amount(round(tot - fee, 8), n_out, rng), float(fee)

    if label == "peel":
        amt = _sample(rng, mu, sigma)
        peel = round(max(_CLAMP_MIN, min(_CLAMP_MAX, round(amt * rng.uniform(0.05, 0.15), 8))), 8)
        fee = _fee_capped(amt, 0.0001)
        change = round(amt - peel - fee, 8)
        if change <= 0:
            peel = round(amt * 0.05, 8)
            change = round(amt - peel - fee, 8)
        if change <= 0:
            change = round((amt - fee) / 2, 8)
            peel = round(amt - fee - change, 8)
        peel = max(_CLAMP_MIN, peel)
        change = max(_CLAMP_MIN, change)
        change = round(amt - peel - fee, 8)
        if change <= 0:
            change = 0.00001
            peel = round(amt - fee - change, 8)
        return [amt], [peel, change], float(fee)

    if label == "structuring":
        n_in, n_out = rng.randint(1, 2), rng.randint(5, 10)
        ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
        tot = round(sum(ins), 8)
        fee = _fee_capped(tot, round(rng.uniform(0.00005, 0.0005), 8))
        out = split_amount(round(tot - fee, 8), n_out, rng)
        mx = max(out) if out else 0
        if mx >= 1.0:
            f = 0.9 / mx
            out = [round(a * f, 8) for a in out]
            out[-1] = round(round(tot - fee, 8) - sum(out[:-1]), 8)
        return ins, out, float(fee)

    if label == "ransomware":
        amt = _sample(rng, mu, sigma)
        n_out = rng.randint(10, 20)
        fee = _fee_capped(amt, round(rng.uniform(0.0001, 0.001), 8))
        return [amt], split_amount(round(amt - fee, 8), n_out, rng), float(fee)

    if label == "bridge":
        n_in = rng.randint(1, 2)
        ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
        tot = round(sum(ins), 8)
        fee = _fee_capped(tot, round(rng.uniform(0.0005, 0.005), 8))
        return ins, [round(tot - fee, 8)], float(fee)

    if label == "high_fee":
        n_in, n_out = rng.randint(1, 2), rng.randint(1, 2)
        ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
        tot = round(sum(ins), 8)
        raw = round(tot * rng.uniform(0.05, 0.20), 8)
        if raw < 0.01:
            raw = 0.01
        fee = _fee_capped(tot, raw)
        if fee < round(tot * 0.05, 8):
            fee = round(tot * 0.05, 8)
            fee = _fee_capped(tot, fee)
        tout = round(tot - fee, 8)
        if tout <= 0:
            fee = round(tot * 0.05, 8)
            tout = round(tot - fee, 8)
        return ins, split_amount(tout, n_out, rng), float(fee)

    if label == "asn_hop":
        n_in, n_out = rng.randint(1, 3), rng.randint(1, 3)
        ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
        tot = round(sum(ins), 8)
        fee = _fee_capped(tot, round(rng.uniform(0.00005, 0.001), 8))
        return ins, split_amount(round(tot - fee, 8), n_out, rng), float(fee)

    # normal
    n_in, n_out = rng.randint(1, 3), rng.randint(1, 3)
    ins = [_sample(rng, mu, sigma) for _ in range(n_in)]
    tot = round(sum(ins), 8)
    fee = _fee_capped(tot, round(rng.uniform(0.00001, 0.001), 8))
    tout = round(tot - fee, 8)
    if tout <= 0:
        fee = _fee_capped(tot, round(tot * 0.01, 8))
        tout = round(tot - fee, 8)
    return ins, split_amount(tout, n_out, rng), float(fee)
