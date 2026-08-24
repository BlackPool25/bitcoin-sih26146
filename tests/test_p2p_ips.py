"""Tests for ml/p2p_ips.py — community-correlated IP assignment."""

from __future__ import annotations

import math
import random
from collections import Counter

from faker import Faker

from ml.graph_sampler import sample_bfs
from ml.p2p_ips import assign_community_ips, build_community_ip_pools


def _rng_faker(seed: int = 42) -> tuple[random.Random, Faker]:
    rng = random.Random(seed)
    faker = Faker()
    Faker.seed(seed)
    faker.seed_instance(seed)
    return rng, faker


def _is_private(ip: str) -> bool:
    try:
        parts = ip.split(".")
        a = int(parts[0])
        b = int(parts[1])
        if a == 10:
            return True
        if a == 192 and b == 168:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        return a == 127
    except Exception:
        return False


def _entropy(vals: list[int]) -> float:
    if not vals:
        return 0.0
    c = Counter(vals)
    tot = float(len(vals))
    ent = 0.0
    for v in c.values():
        p = float(v) / tot
        if p > 0:
            ent -= p * math.log(p + 1e-12)
    return float(ent)


def test_5k_unique() -> None:
    rng, faker = _rng_faker(42)
    sub = sample_bfs(None, n=50000, seed=42)
    res = assign_community_ips(sub, rng, faker, n_unique=5000)
    uniq: set[str] = set()
    for r in res.values():
        uniq.add(r.src_ip)
        uniq.add(r.dst_ip)
    assert len(uniq) == 5000, f"expected 5000 unique ips, got {len(uniq)}"
    pools = build_community_ip_pools(sub, rng, faker)
    for cid, lst in pools.items():
        assert 20 <= len(lst) <= 800, f"pool {cid} size {len(lst)} out of 20-800"
    assert all(len(set(v)) == len(v) for v in pools.values())


def test_countries_ge_8() -> None:
    rng, faker = _rng_faker(42)
    sub = sample_bfs(None, n=50000, seed=42)
    res = assign_community_ips(sub, rng, faker, n_unique=5000)
    countries: set[str] = {r.geo_country for r in res.values()}
    assert len(countries) >= 8, f"expected >=8 countries, got {len(countries)} {countries}"
    rng2, faker2 = _rng_faker(7)
    res2 = assign_community_ips(None, rng2, faker2, n_unique=5000)
    countries2: set[str] = {r.geo_country for r in res2.values()}
    assert len(countries2) >= 8, f"fallback expected >=8 got {len(countries2)}"


def test_geo_asn_n_unique_gt_1000() -> None:
    rng, faker = _rng_faker(42)
    sub = sample_bfs(None, n=50000, seed=42)
    res = assign_community_ips(sub, rng, faker, n_unique=5000)
    asns: set[int] = {r.geo_asn for r in res.values()}
    assert len(asns) > 1000, f"expected >1000 distinct asn, got {len(asns)}"
    for a in asns:
        assert 1000 <= a <= 500000, f"asn {a} out of range"


def test_tor_and_port_entropy() -> None:
    rng, faker = _rng_faker(42)
    sub = sample_bfs(None, n=50000, seed=42)
    res = assign_community_ips(sub, rng, faker, n_unique=5000)
    total_ips: int = 2 * len(res)
    priv_count: int = 0
    for r in res.values():
        if _is_private(r.src_ip):
            priv_count += 1
        if _is_private(r.dst_ip):
            priv_count += 1
    priv_rate: float = priv_count / total_ips if total_ips else 0.0
    assert 0.02 <= priv_rate <= 0.07, f"priv rate {priv_rate:.4f} not in 2-7%"
    tor_flag: float = sum(1 for r in res.values() if _is_private(r.src_ip) or _is_private(r.dst_ip)) / len(res) if res else 0.0
    assert 0.02 <= tor_flag <= 0.15, f"tor flag {tor_flag:.4f} not in 2-15%"
    ports: list[int] = [r.src_port for r in res.values()] + [r.dst_port for r in res.values()]
    ent: float = _entropy(ports)
    assert ent > 0.0, f"port entropy {ent} not >0"
    assert set(ports).issubset({8333, 18333, 9735})
    assert len(set(ports)) >= 2
    rng2, faker2 = _rng_faker(99)
    res2 = assign_community_ips(None, rng2, faker2, n_unique=5000)
    ports2: list[int] = [r.src_port for r in res2.values()]
    ent2: float = _entropy(ports2)
    assert ent2 > 0.0
