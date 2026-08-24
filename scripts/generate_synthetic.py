#!/usr/bin/env python3
"""Elliptic-anchored 50K/80K/5K synthetic generator + csv|json|xml exports."""

# allow: SIZE_OK — 8 injection patterns + 3 exporters in single CLI seam

from __future__ import annotations

import argparse
import collections
import contextlib
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
from faker import Faker
from lxml import etree  # type: ignore[import-untyped]

from backend.ingest.models import TransactionRecord

# ---------------------------------------------------------------------------
# Dual-path flag + optional ml imports (suppressed so fallback never breaks)
# ---------------------------------------------------------------------------
ELLIPTIC_AVAILABLE: bool = Path("data/raw/elliptic/elliptic_txs_features.csv").exists()

_load_elliptic: Any = None
_get_amount_stats: Any = None
_sample_bfs: Any = None
_build_amounts_lognormal: Any = None
_generate_timestamps: Any = None
_elliptic_base_time: Any = None
_assign_community_ips: Any = None

with contextlib.suppress(Exception):  # pragma: no cover - import guard
    from ml.amounts import build_amounts_lognormal as _build_amounts_lognormal  # type: ignore
    from ml.elliptic_loader import get_amount_stats as _get_amount_stats  # type: ignore
    from ml.elliptic_loader import load_elliptic as _load_elliptic  # type: ignore
    from ml.graph_sampler import sample_bfs as _sample_bfs  # type: ignore
    from ml.p2p_ips import assign_community_ips as _assign_community_ips  # type: ignore
    from ml.temporal import elliptic_base_time as _elliptic_base_time  # type: ignore
    from ml.temporal import generate_timestamps as _generate_timestamps  # type: ignore

SCALE_MAP: dict[str, int] = {"1k": 1000, "10k": 10000, "50k": 50000, "80k": 80000}
COUNTRIES: list[str] = [
    "US",
    "CN",
    "RU",
    "DE",
    "JP",
    "GB",
    "IN",
    "BR",
    "CA",
    "AU",
    "FR",
    "KR",
    "NL",
    "SG",
    "TR",
    "NG",
    "ZA",
    "IR",
    "UA",
    "SE",
]
SCRIPT_TYPES: list[str] = ["P2PKH", "P2SH", "P2WPKH", "P2WSH", "unknown"]
SCRIPT_WEIGHTS: list[float] = [0.25, 0.2, 0.4, 0.1, 0.05]
BASE58: str = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
LABELS: list[str] = [
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
# illicit 4% total, split among 8 patterns ~0.5% each
ILLICIT_RATE = 0.04
RISK_MAP: dict[str, str] = {
    "normal": "low",
    "peel": "high",
    "mixer": "high",
    "coinjoin": "medium",
    "structuring": "medium",
    "ransomware": "critical",
    "bridge": "high",
    "high_fee": "medium",
    "asn_hop": "low",
}


def random_address(rng: random.Random, prefix_choice: str | None = None) -> str:
    if prefix_choice is None:
        r = rng.random()
        if r < 0.5:
            prefix = "1"
        elif r < 0.8:
            prefix = "3"
        else:
            prefix = "bc1"
    else:
        prefix = prefix_choice
    # length 26-35 inclusive for 1/3 prefix; bc1 is longer (42-62) but we mimic 26-35 after prefix
    if prefix == "bc1":
        body_len = rng.randint(20, 38)
        # bech32 alphabet simplified as base58 for mock
        body = "".join(rng.choices(BASE58.lower(), k=body_len))
        return prefix + body
    length = rng.randint(26, 35)
    body_len = length - len(prefix)
    body = "".join(rng.choices(BASE58, k=body_len))
    return prefix + body


def random_txid(rng: random.Random) -> str:
    # 64 hex chars, use getrandbits + hashlib fallback for uniformity
    v = rng.getrandbits(256)
    hx = format(v, "064x")
    # ensure lowercase hex (already) and mix hashlib for extra diffusion if needed
    if len(hx) != 64:
        hx = hashlib.sha256(str(rng.random()).encode()).hexdigest()
    return hx


def split_amount(total: float, n: int, rng: random.Random) -> list[float]:
    if n == 1:
        return [round(total, 8)]
    # generate n random weights
    weights = [rng.random() + 0.1 for _ in range(n)]
    s = sum(weights)
    raw = [w / s * total for w in weights]
    # round to 8 decimals, adjust last to fix sum
    rounded = [round(x, 8) for x in raw]
    diff = round(total - sum(rounded), 8)
    rounded[-1] = round(rounded[-1] + diff, 8)
    # ensure no negative due to rounding
    if rounded[-1] <= 0:
        rounded[-1] = round(total - sum(rounded[:-1]), 8)
    # ensure all >0
    for i, v in enumerate(rounded):
        if v <= 0:
            rounded[i] = 0.00001
    # re-normalize if needed
    # final adjustment to keep sum = total
    rounded[-1] = round(total - sum(rounded[:-1]), 8)
    return rounded


def generate_ip_pool(rng: random.Random, faker: Faker, n_unique: int) -> list[str]:
    pool: set[str] = set()
    # Use faker ipv4 for realism; fallback to rng generation if dupes stall
    attempts = 0
    while len(pool) < n_unique and attempts < n_unique * 10:
        ip = faker.ipv4_private() if rng.random() < 0.05 else faker.ipv4()
        # faker may return private; we want public mostly, but validation accepts any IPv4
        # filter to avoid 0.0.0.0 / 255 etc already handled by faker
        pool.add(ip)
        attempts += 1
    # fallback fill with rng
    while len(pool) < n_unique:
        ip = f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"  # noqa: E501
        pool.add(ip)
    return list(pool)


def choose_label(rng: random.Random) -> str:
    if rng.random() >= ILLICIT_RATE:
        return "normal"
    # pick among 8 illicit uniformly
    illicit = LABELS[1:]
    return rng.choice(illicit)


def build_amounts_for_label(
    label: str, rng: random.Random
) -> tuple[list[float], list[float], float]:
    # Returns (input_amounts, output_amounts, fee)
    if label == "coinjoin":
        n = 22
        # 22 inputs/outputs equal 0.01, fee small
        in_amt = 0.0101
        out_amt = 0.01
        in_amts = [round(in_amt, 8) for _ in range(n)]
        out_amts = [round(out_amt, 8) for _ in range(n)]
        fee = round(n * (in_amt - out_amt), 8)
        return in_amts, out_amts, float(fee)
    if label == "mixer":
        # random fan-in vs fan-out
        if rng.random() < 0.5:
            n_in = rng.randint(5, 10)
            n_out = rng.randint(1, 2)
        else:
            n_in = rng.randint(1, 2)
            n_out = rng.randint(5, 10)
        in_amts = [round(rng.uniform(0.1, 3.0), 8) for _ in range(n_in)]
        total_in = sum(in_amts)
        fee = round(rng.uniform(0.0001, 0.002), 8)
        total_out = round(total_in - fee, 8)
        out_amts = split_amount(total_out, n_out, rng)
        return in_amts, out_amts, float(fee)
    if label == "peel":
        n_in = 1
        n_out = 2
        in_amt = round(rng.uniform(1.0, 5.0), 8)
        peel_amt = round(in_amt * rng.uniform(0.05, 0.15), 8)
        fee = 0.0001
        change_amt = round(in_amt - peel_amt - fee, 8)
        return [in_amt], [peel_amt, change_amt], float(fee)
    if label == "structuring":
        n_in = rng.randint(1, 2)
        n_out = rng.randint(5, 10)
        in_amts = [round(rng.uniform(0.5, 5.0), 8) for _ in range(n_in)]
        total_in = sum(in_amts)
        fee = round(rng.uniform(0.00005, 0.0005), 8)
        total_out = round(total_in - fee, 8)
        # ensure each output <1 BTC
        # split then cap, re-split if needed
        out_amts = split_amount(total_out, n_out, rng)
        # if any >=1, scale down proportionally (already <1 if total <5 and n>=5 usually ok)
        # force <0.9
        max_out = max(out_amts) if out_amts else 0
        if max_out >= 1.0:
            # rescale to ensure max 0.9
            factor = 0.9 / max_out
            out_amts = [round(a * factor, 8) for a in out_amts]
            # adjust to keep sum = total_out (allow slight deviation, fee absorbs)
            out_amts[-1] = round(total_out - sum(out_amts[:-1]), 8)
        return in_amts, out_amts, float(fee)
    if label == "ransomware":
        n_in = 1
        n_out = rng.randint(10, 20)
        in_amt = round(rng.uniform(2.0, 10.0), 8)
        fee = round(rng.uniform(0.0001, 0.001), 8)
        total_out = round(in_amt - fee, 8)
        out_amts = split_amount(total_out, n_out, rng)
        return [in_amt], out_amts, float(fee)
    if label == "bridge":
        n_in = rng.randint(1, 2)
        n_out = 1
        in_amts = [round(rng.uniform(0.5, 10.0), 8) for _ in range(n_in)]
        total_in = sum(in_amts)
        fee = round(rng.uniform(0.0005, 0.005), 8)
        out_amts = [round(total_in - fee, 8)]
        return in_amts, out_amts, float(fee)
    if label == "high_fee":
        n_in = rng.randint(1, 2)
        n_out = rng.randint(1, 2)
        in_amts = [round(rng.uniform(0.1, 1.0), 8) for _ in range(n_in)]
        total_in = sum(in_amts)
        # fee 5-20% of total
        fee = round(total_in * rng.uniform(0.05, 0.20), 8)
        if fee < 0.01:
            fee = 0.01
        total_out = round(total_in - fee, 8)
        out_amts = split_amount(total_out, n_out, rng)
        return in_amts, out_amts, float(fee)
    if label == "asn_hop":
        n_in = rng.randint(1, 3)
        n_out = rng.randint(1, 3)
        in_amts = [round(rng.uniform(0.01, 2.0), 8) for _ in range(n_in)]
        total_in = sum(in_amts)
        fee = round(rng.uniform(0.00005, 0.001), 8)
        total_out = round(total_in - fee, 8)
        out_amts = split_amount(total_out, n_out, rng)
        return in_amts, out_amts, float(fee)
    # normal
    n_in = rng.randint(1, 3)
    n_out = rng.randint(1, 3)
    in_amts = [round(rng.uniform(0.001, 5.0), 8) for _ in range(n_in)]
    total_in = sum(in_amts)
    fee = round(rng.uniform(0.00001, 0.001), 8)
    total_out = round(total_in - fee, 8)
    # ensure total_out positive
    if total_out <= 0:
        fee = round(total_in * 0.01, 8)
        total_out = round(total_in - fee, 8)
    out_amts = split_amount(total_out, n_out, rng)
    return in_amts, out_amts, float(fee)


def generate_records(
    rng: random.Random,
    faker: Faker,
    n: int,
    sigma: int,
    ip_pool: list[str],
    base_now: datetime,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    # track peel chains for realism: keep last change address per chain
    for i in range(n):
        label = choose_label(rng)
        risk_tier = RISK_MAP[label]
        src_ip = rng.choice(ip_pool)
        dst_ip = rng.choice(ip_pool)
        # ensure src != dst occasionally
        if src_ip == dst_ip and rng.random() < 0.9:
            dst_ip = rng.choice(ip_pool)
        src_port = rng.randint(8333, 18333)
        dst_port = rng.randint(8333, 18333)
        # timestamp = now +- Gaussian jitter N(0, sigma seconds) per spec
        jitter = rng.gauss(0, float(sigma))
        ts = base_now + timedelta(seconds=jitter)
        # txid
        txid = random_txid(rng)
        in_amts, out_amts, fee = build_amounts_for_label(label, rng)
        n_in = len(in_amts)
        n_out = len(out_amts)
        in_addrs = [random_address(rng) for _ in range(n_in)]
        out_addrs = [random_address(rng) for _ in range(n_out)]
        script_type = rng.choices(SCRIPT_TYPES, weights=SCRIPT_WEIGHTS, k=1)[0]
        geo_country = rng.choice(COUNTRIES)
        # for asn_hop, ensure geo mismatch hints by picking distinct country for dst
        if label == "asn_hop" and rng.random() < 0.7:
            # pick dst country different; we store only one geo_country per tx (src geo)
            # so flip to a different one deterministically
            alt = rng.choice([c for c in COUNTRIES if c != geo_country])
            geo_country = alt
        geo_asn = rng.randint(1000, 500000)
        rec: dict[str, Any] = {
            "timestamp": ts,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "txid": txid,
            "input_addresses": in_addrs,
            "output_addresses": out_addrs,
            "input_amounts": in_amts,
            "output_amounts": out_amts,
            "fee": float(fee),
            "script_type": script_type,
            "geo_country": geo_country,
            "geo_asn": int(geo_asn),
            "injection_label": label,
            "risk_tier": risk_tier,
        }
        # track index for debugging
        _ = i
        records.append(rec)
    # ensure txid uniqueness
    seen: set[str] = set()
    for r in records:
        while r["txid"] in seen:
            r["txid"] = random_txid(rng)
        seen.add(r["txid"])
    return records


# ---------------------------------------------------------------------------
# Fallback wrapper (preserves original generate_records unchanged for alias)
# ---------------------------------------------------------------------------
def fallback_faker_path(
    n: int,
    sigma: int,
    seed: int,
    rng: random.Random,
    faker: Faker,
) -> tuple[list[dict[str, Any]], datetime, list[str]]:
    """Faker fallback path — identical to original main logic."""
    n_unique = max(1, n // 10)
    ip_pool = generate_ip_pool(rng, faker, n_unique)
    base_now = datetime.now(UTC)
    records = generate_records(rng, faker, n, sigma, ip_pool, base_now)
    return records, base_now, ip_pool


# ---------------------------------------------------------------------------
# Elliptic-anchored path
# ---------------------------------------------------------------------------
def elliptic_anchored_path(
    n: int,
    sigma: int,
    seed: int,
    rng: random.Random,
    faker: Faker,
) -> tuple[list[dict[str, Any]], datetime, list[str]] | None:
    """Anchored path via ml.elliptic_loader + ml.graph_sampler + ml.amounts + ml.temporal + ml.p2p_ips.

    Returns None if elliptic data or ml modules unavailable → caller falls back.
    Deterministic base_time = 2024-01-01 + seed%30 (not now()).
    """
    # Guard: need flag and all ml callables
    if not ELLIPTIC_AVAILABLE:
        return None
    if any(
        x is None
        for x in (
            _load_elliptic,
            _sample_bfs,
            _assign_community_ips,
            _generate_timestamps,
            _elliptic_base_time,
            _build_amounts_lognormal,
        )
    ):
        return None
    try:
        g = _load_elliptic()  # type: ignore[misc]
    except Exception:
        return None
    if g is None:
        return None
    try:
        s = _sample_bfs(g, n=n, seed=seed)  # type: ignore[misc]
    except Exception:
        return None
    if s is None or s.nodes.height == 0:
        return None

    # Amount stats (per numeric label) — passed to lognormal builder; falls back to priors if mismatched
    stats: Any = None
    with contextlib.suppress(Exception):
        if _get_amount_stats is not None:
            stats = _get_amount_stats(g)  # type: ignore[misc]

    # Community-correlated IPs
    try:
        ip_map = _assign_community_ips(s, rng, faker, n_unique=max(1, n // 10))  # type: ignore[misc]
    except Exception:
        ip_map = None

    # DAG-aware timestamps with deterministic base
    try:
        base_time: datetime = _elliptic_base_time(seed)  # type: ignore[misc]
    except Exception:
        base_time = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=int(seed % 30))
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=UTC)
    try:
        ts_list: list[datetime] | None = _generate_timestamps(s, rng, sigma, base_time, n_fallback=n)  # type: ignore[misc]
    except Exception:
        ts_list = None

    # Build txid list from sampled subgraph nodes (first column is txId)
    try:
        tx_col = s.nodes.columns[0]
        sampled_txids: list[str] = [str(v) for v in s.nodes[tx_col].to_list()]
    except Exception:
        return None
    if len(sampled_txids) == 0:
        return None
    # Ensure length n (sample_bfs guarantees n, but handle n>graph)
    if len(sampled_txids) < n:
        # pad with synthetic txids (fallback to faker-style) for determinism
        for i in range(n - len(sampled_txids)):
            sampled_txids.append(hashlib.sha256(f"{seed}:pad:{i}".encode()).hexdigest()[:64].ljust(64, "0"))
    elif len(sampled_txids) > n:
        sampled_txids = sampled_txids[:n]

    # Injection plan invert: txid -> label
    tx_to_label: dict[str, str] = {}
    try:
        plan: dict[str, list[str]] = dict(s.injection_plan) if isinstance(s.injection_plan, dict) else {}
        # _plan keys are peel_chain, mixer_merge, coinjoin, etc. Map to LABELS
        key_to_label: dict[str, str] = {
            "peel_chain": "peel",
            "mixer_merge": "mixer",
            "coinjoin": "coinjoin",
            "ransomware": "ransomware",
            "structuring": "structuring",
            "bridge": "bridge",
            "high_fee": "high_fee",
            "asn_hop": "asn_hop",
        }
        for k, lst in plan.items():
            lbl = key_to_label.get(k, k)
            for tx in lst:
                tx_to_label[str(tx)] = lbl
    except Exception:
        tx_to_label = {}

    # Align timestamps: ts_list is topo-ordered; map via index fallback to sequential assignment.
    # If ts_list length mismatches, fallback to base_time + jitter per record.
    if ts_list is None or len(ts_list) != n:
        # fallback jitter timestamps deterministic but anchored to base_time
        ts_list = []
        for _ in range(n):
            jitter = rng.gauss(0, float(sigma))
            ts_list.append(base_time + timedelta(seconds=float(jitter)))

    # Align ip_map: if None or missing entries, fallback to faker pool
    fallback_ip_pool: list[str] | None = None
    if ip_map is None or len(ip_map) == 0:
        fallback_ip_pool = generate_ip_pool(rng, faker, max(1, n // 10))

    records: list[dict[str, Any]] = []
    seen_tx: set[str] = set()
    ip_pool_for_meta: list[str] = []
    # collect unique IPs for meta
    unique_ips: set[str] = set()

    for idx, raw_txid in enumerate(sampled_txids):
        # Determine label: injection plan or choose_label fallback
        label = tx_to_label.get(raw_txid)
        if label is None or label not in LABELS:
            # Use deterministic but still ~4% illicit: reuse rng state
            label = choose_label(rng)
        risk_tier = RISK_MAP[label]

        # Txid: use sampled elliptic txid if it looks like 64-hex, else generate synthetic
        txid = str(raw_txid)
        # elliptic txIds may not be 64-hex (could be sha-like but ensure valid)
        if len(txid) != 64 or any(c not in "0123456789abcdef" for c in txid.lower()):
            # hash to 64 hex deterministic
            txid = hashlib.sha256(f"{seed}:{txid}".encode()).hexdigest()
        txid = txid.lower()
        # ensure uniqueness (sampled should be unique, but pad may dup)
        while txid in seen_tx:
            txid = random_txid(rng)
        seen_tx.add(txid)

        ts = ts_list[idx] if idx < len(ts_list) else base_time + timedelta(seconds=float(rng.gauss(0, float(sigma))))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        # IP/geo/ports via community map or fallback
        if ip_map is not None and raw_txid in ip_map:
            rec_ip = ip_map[raw_txid]
            src_ip = str(rec_ip.src_ip)
            dst_ip = str(rec_ip.dst_ip)
            src_port = int(rec_ip.src_port)
            dst_port = int(rec_ip.dst_port)
            geo_country = str(rec_ip.geo_country)
            geo_asn = int(rec_ip.geo_asn)
        elif ip_map is not None and len(ip_map) > 0:
            # pick random from map values for padded ids
            vals = list(ip_map.values())
            chosen = rng.choice(vals)
            src_ip = str(chosen.src_ip)
            dst_ip = str(chosen.dst_ip)
            src_port = int(chosen.src_port)
            dst_port = int(chosen.dst_port)
            geo_country = str(chosen.geo_country)
            geo_asn = int(chosen.geo_asn)
        else:
            assert fallback_ip_pool is not None
            src_ip = rng.choice(fallback_ip_pool)
            dst_ip = rng.choice(fallback_ip_pool)
            if src_ip == dst_ip and rng.random() < 0.9:
                dst_ip = rng.choice(fallback_ip_pool)
            src_port = rng.randint(8333, 18333)
            dst_port = rng.randint(8333, 18333)
            geo_country = rng.choice(COUNTRIES)
            if label == "asn_hop" and rng.random() < 0.7:
                alt = rng.choice([c for c in COUNTRIES if c != geo_country])
                geo_country = alt
            geo_asn = rng.randint(1000, 500000)

        # Amounts via lognormal, fallback to build_amounts_for_label if stats None or error
        in_amts: list[float]
        out_amts: list[float]
        fee: float
        try:
            if _build_amounts_lognormal is not None:
                # stats may be dict[int, tuple] — _get_mu_sigma handles string label lookup with fallback to priors
                in_amts, out_amts, fee = _build_amounts_lognormal(label, rng, stats)  # type: ignore[misc]
            else:
                raise RuntimeError("no lognormal builder")
        except Exception:
            in_amts, out_amts, fee = build_amounts_for_label(label, rng)

        n_in = len(in_amts)
        n_out = len(out_amts)
        in_addrs = [random_address(rng) for _ in range(n_in)]
        out_addrs = [random_address(rng) for _ in range(n_out)]
        script_type = rng.choices(SCRIPT_TYPES, weights=SCRIPT_WEIGHTS, k=1)[0]
        # For asn_hop with community IPs, country already set via ip_map; but keep mismatch hint
        if label == "asn_hop" and ip_map is not None and rng.random() < 0.3:
            # occasionally flip to ensure diversity
            alt2 = rng.choice([c for c in COUNTRIES if c != geo_country])
            geo_country = alt2

        rec: dict[str, Any] = {
            "timestamp": ts,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "txid": txid,
            "input_addresses": in_addrs,
            "output_addresses": out_addrs,
            "input_amounts": in_amts,
            "output_amounts": out_amts,
            "fee": float(fee),
            "script_type": script_type,
            "geo_country": geo_country,
            "geo_asn": int(geo_asn),
            "injection_label": label,
            "risk_tier": risk_tier,
        }
        unique_ips.add(src_ip)
        unique_ips.add(dst_ip)
        records.append(rec)

    # ip_pool_for_meta: derive from map or fallback
    if ip_map is not None and len(ip_map) > 0:
        # Use scaled pool size as recorded
        pool_ips: set[str] = set()
        for v in ip_map.values():
            pool_ips.add(str(v.src_ip))
            pool_ips.add(str(v.dst_ip))
        ip_pool_for_meta = list(pool_ips)
        # ensure at least n//10 accounted; if map larger, keep as is
        if len(ip_pool_for_meta) == 0 and fallback_ip_pool is not None:
            ip_pool_for_meta = fallback_ip_pool
    else:
        ip_pool_for_meta = fallback_ip_pool if fallback_ip_pool is not None else []

    return records, base_time, ip_pool_for_meta


def validate_sample(records: list[dict[str, Any]], sample_n: int = 10) -> None:
    # sample deterministically first sample_n or random 10
    n = min(sample_n, len(records))
    # pick evenly spaced indices for coverage
    if len(records) <= n:
        idxs = list(range(len(records)))
    else:
        step = len(records) // n
        idxs = [i * step for i in range(n)]
    for idx in idxs:
        raw = records[idx]
        # strip extra fields not in TransactionRecord
        core = {k: v for k, v in raw.items() if k not in ("injection_label", "risk_tier")}
        # TransactionRecord accepts datetime or iso string, list fields, etc.
        TransactionRecord.model_validate(core)


def write_csv(records: list[dict[str, Any]], path: Path) -> None:
    # Build polars DataFrame with json-encoded arrays for CSV
    rows: list[dict[str, Any]] = []
    for r in records:
        # timestamp iso with Z
        ts: datetime = r["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        iso = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
        rows.append(
            {
                "timestamp": iso,
                "src_ip": r["src_ip"],
                "dst_ip": r["dst_ip"],
                "src_port": r["src_port"],
                "dst_port": r["dst_port"],
                "txid": r["txid"],
                "input_addresses": json.dumps(r["input_addresses"]),
                "output_addresses": json.dumps(r["output_addresses"]),
                "input_amounts": json.dumps(r["input_amounts"]),
                "output_amounts": json.dumps(r["output_amounts"]),
                "fee": float(r["fee"]),
                "script_type": r["script_type"],
                "geo_country": r["geo_country"],
                "geo_asn": int(r["geo_asn"]),
                "injection_label": r["injection_label"],
                "risk_tier": r["risk_tier"],
            }
        )
    df = pl.DataFrame(rows)
    # ensure column order
    order = [
        "timestamp",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "txid",
        "input_addresses",
        "output_addresses",
        "input_amounts",
        "output_amounts",
        "fee",
        "script_type",
        "geo_country",
        "geo_asn",
        "injection_label",
        "risk_tier",
    ]
    df = df.select(order)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(str(path))


def write_json(records: list[dict[str, Any]], path: Path) -> None:
    out: list[dict[str, Any]] = []
    for r in records:
        ts: datetime = r["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        iso = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
        out.append(
            {
                "timestamp": iso,
                "src_ip": r["src_ip"],
                "dst_ip": r["dst_ip"],
                "src_port": r["src_port"],
                "dst_port": r["dst_port"],
                "txid": r["txid"],
                "input_addresses": r["input_addresses"],
                "output_addresses": r["output_addresses"],
                "input_amounts": r["input_amounts"],
                "output_amounts": r["output_amounts"],
                "fee": float(r["fee"]),
                "script_type": r["script_type"],
                "geo_country": r["geo_country"],
                "geo_asn": int(r["geo_asn"]),
                "injection_label": r["injection_label"],
                "risk_tier": r["risk_tier"],
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def write_xml(records: list[dict[str, Any]], path: Path) -> None:
    root = etree.Element("records")
    for r in records:
        rec_el = etree.SubElement(root, "record")
        ts: datetime = r["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        iso = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
        fields: dict[str, str] = {
            "timestamp": iso,
            "src_ip": str(r["src_ip"]),
            "dst_ip": str(r["dst_ip"]),
            "src_port": str(r["src_port"]),
            "dst_port": str(r["dst_port"]),
            "txid": str(r["txid"]),
            "input_addresses": json.dumps(r["input_addresses"]),
            "output_addresses": json.dumps(r["output_addresses"]),
            "input_amounts": json.dumps(r["input_amounts"]),
            "output_amounts": json.dumps(r["output_amounts"]),
            "fee": str(float(r["fee"])),
            "script_type": str(r["script_type"]),
            "geo_country": str(r["geo_country"]),
            "geo_asn": str(int(r["geo_asn"])),
            "injection_label": str(r["injection_label"]),
            "risk_tier": str(r["risk_tier"]),
        }
        for k, v in fields.items():
            child = etree.SubElement(rec_el, k)
            child.text = v
    tree = etree.ElementTree(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Elliptic-anchored synthetic generator (faker+Gaussian jitter; falls back to Faker when elliptic data missing)"
    )
    p.add_argument(
        "--scale",
        choices=["1k", "10k", "50k", "80k"],
        default="50k",
        help="Scale mapping: 1k=1000, 10k=10000, 50k=50000, 80k=80000 (default 50k)",
    )
    p.add_argument(
        "--sigma",
        type=int,
        choices=[5, 30, 120],
        default=30,
        help="Gaussian jitter sigma seconds (5,30,120)",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["csv", "json", "xml", "all"],
        default="all",
        help="Export format (default all)",
    )
    p.add_argument(
        "--out",
        type=str,
        default="data/raw/synthetic",
        help="Output directory (default data/raw/synthetic)",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    n = SCALE_MAP[args.scale]
    sigma: int = int(args.sigma)
    fmt: str = str(args.fmt)
    out_dir = Path(str(args.out))
    seed: int = int(args.seed)

    rng = random.Random(seed)
    faker = Faker()
    Faker.seed(seed)
    faker.seed_instance(seed)

    # Try elliptic-anchored path first; fallback to faker
    records: list[dict[str, Any]] | None = None
    base_now: datetime | None = None
    ip_pool: list[str] | None = None
    elliptic_anchored = False
    amount_lognormal = False

    anchored = elliptic_anchored_path(n, sigma, seed, rng, faker)
    if anchored is not None:
        records, base_now, ip_pool = anchored
        elliptic_anchored = True
        amount_lognormal = True
        # Re-seed rng/faker are already advanced via anchored path (intentional deterministic)
    else:
        # Fallback faker path (preserves original logic exactly)
        if ELLIPTIC_AVAILABLE and _load_elliptic is not None:
            # ELLIPTIC_AVAILABLE true but load failed (empty files) -> still warn fallback
            print("WARN: elliptic data unavailable or load failed — using faker fallback", flush=True)
        elif not ELLIPTIC_AVAILABLE:
            print("WARN: elliptic data not found — using faker fallback", flush=True)
        records, base_now, ip_pool = fallback_faker_path(n, sigma, seed, rng, faker)
        elliptic_anchored = False
        amount_lognormal = False
        # For fallback, generation_mode is faker_fallback; base_now is now(UTC) per original

    assert records is not None and base_now is not None and ip_pool is not None

    # Validate sampled rows via TransactionRecord
    validate_sample(records, 10)

    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"synth_{args.scale}"
    written: list[str] = []

    if fmt in ("csv", "all"):
        csv_path = out_dir / f"{base}.csv"
        write_csv(records, csv_path)
        written.append(str(csv_path))
    if fmt in ("json", "all"):
        json_path = out_dir / f"{base}.json"
        write_json(records, json_path)
        written.append(str(json_path))
    if fmt in ("xml", "all"):
        xml_path = out_dir / f"{base}.xml"
        write_xml(records, xml_path)
        written.append(str(xml_path))

    # sidecar meta
    injection_counts = dict(collections.Counter(r["injection_label"] for r in records))
    risk_counts = dict(collections.Counter(r["risk_tier"] for r in records))
    script_counts = dict(collections.Counter(r["script_type"] for r in records))
    generation_mode = "elliptic_anchored" if elliptic_anchored else "faker_fallback"
    meta = {
        "scale": args.scale,
        "scale_n": n,
        "sigma": sigma,
        "seed": seed,
        "n_rows": len(records),
        "n_unique_ips": len(ip_pool),
        "format": fmt,
        "files": written,
        "injection_counts": injection_counts,
        "risk_tier_counts": risk_counts,
        "script_type_counts": script_counts,
        "generated_at": base_now.isoformat().replace("+00:00", "Z"),
        "elliptic_anchored": bool(elliptic_anchored),
        "generation_mode": str(generation_mode),
        "bfs_seed": int(seed),
        "amount_lognormal": bool(amount_lognormal),
    }
    meta_path = out_dir / f"{base}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {len(records)} rows (scale {args.scale}={n}, sigma={sigma}) -> {out_dir} [{generation_mode}]")
    print(f"  files: {', '.join(written)}")
    print(f"  meta: {meta_path}")
    print(f"  elliptic_anchored: {elliptic_anchored}")
    print(f"  injection_counts: {injection_counts}")
    # quick txid sample
    for r in records[:2]:
        print(f"  sample txid {r['txid'][:16]}... label={r['injection_label']}")


if __name__ == "__main__":
    main()
