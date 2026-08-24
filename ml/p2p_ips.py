"""ml/p2p_ips.py — community-correlated IP assignment."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass

from faker import Faker

from ml.graph_sampler import SampledSubgraph

COUNTRIES: list[str] = [
    "US", "CN", "RU", "DE", "JP", "GB", "IN", "BR", "CA", "AU",
    "FR", "KR", "NL", "SG", "TR", "NG", "ZA", "IR", "UA", "SE",
]


@dataclass(frozen=True, slots=True)
class IpRecord:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    geo_country: str
    geo_asn: int


def _hi(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:16], 16)


def _country_cid(cid: int) -> str:
    return COUNTRIES[_hi(str(cid)) % len(COUNTRIES)]


def _country_tx(txid: str) -> str:
    return COUNTRIES[_hi(txid) % len(COUNTRIES)]


def _asn(cid: int, txid: str) -> int:
    return 1000 + (_hi(f"{cid}:{txid}") % 499001)


def _asn_fb(txid: str) -> int:
    return 1000 + (_hi(txid) % 499001)


def _port(txid: str, role: str) -> int:
    h: int = _hi(f"{txid}:{role}")
    if h % 10 < 6:
        return 8333
    return 18333 if h % 2 == 0 else 9735


def _gen_ip(rng: random.Random, faker: Faker) -> str:
    if rng.random() < 0.05:
        try:
            return str(faker.ipv4_private())
        except Exception:
            pass
    try:
        return str(faker.ipv4())
    except Exception:
        return f"{rng.randint(1,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"


def _gen_pool(rng: random.Random, faker: Faker, size: int) -> list[str]:
    pool: set[str] = set()
    attempts: int = 0
    while len(pool) < size and attempts < size * 10:
        pool.add(_gen_ip(rng, faker))
        attempts += 1
    while len(pool) < size:
        ip: str = f"{rng.randint(1,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"
        pool.add(ip)
    return list(pool)


def build_community_ip_pools(
    subgraph: SampledSubgraph | None,
    rng: random.Random,
    faker: Faker,
) -> dict[int, list[str]]:
    if subgraph is None or not subgraph.communities:
        return {0: _gen_pool(rng, faker, 5000)}
    counts: Counter[int] = Counter(subgraph.communities.values())
    if not counts:
        return {0: _gen_pool(rng, faker, 5000)}
    mn: int = min(counts.values())
    mx: int = max(counts.values())
    out: dict[int, list[str]] = {}
    for cid, sz in counts.items():
        if mx == mn:
            raw: int = 400
        else:
            raw = 20 + int((sz - mn) / (mx - mn) * 780)
        raw = max(20, min(800, raw))
        out[int(cid)] = _gen_pool(rng, faker, raw)
    return out


def _scaled_pools(
    counts: Counter[int],
    total_nodes: int,
    n_unique: int,
    rng: random.Random,
    faker: Faker,
) -> dict[int, list[str]]:
    mn: int = min(counts.values())
    mx: int = max(counts.values())
    raw: dict[int, int] = {}
    for cid, sz in counts.items():
        if mx == mn:
            v: int = max(20, n_unique // max(1, len(counts)))
        else:
            share: int = int(round(sz / total_nodes * n_unique))
            frac: float = (sz - mn) / (mx - mn)
            base: int = 20 + int(frac * 780)
            v = max(20, min(800, max(share, base) if n_unique > 2000 else share))
            v = max(20, min(800, v))
        raw[int(cid)] = v
    s: int = sum(raw.values())
    if s != n_unique and s > 0:
        scale: float = n_unique / s
        sc: dict[int, int] = {c: max(20, min(800, int(round(v * scale)))) for c, v in raw.items()}
        diff: int = n_unique - sum(sc.values())
        order: list[int] = sorted(sc.keys(), key=lambda c: counts.get(c, 0), reverse=True)
        i: int = 0
        while diff != 0 and order:
            cid2: int = order[i % len(order)]
            if diff > 0 and sc[cid2] < 800:
                sc[cid2] += 1
                diff -= 1
            elif diff < 0 and sc[cid2] > 20:
                sc[cid2] -= 1
                diff += 1
            else:
                # skip if clamped, try next
                pass
            i += 1
            if i > n_unique * 3:
                break
        raw = sc
    pools: dict[int, list[str]] = {}
    seen: set[str] = set()
    for cid, sz2 in raw.items():
        lst: list[str] = _gen_pool(rng, faker, sz2)
        # dedup across pools
        uniq: list[str] = []
        for ip in lst:
            if ip not in seen:
                uniq.append(ip)
                seen.add(ip)
        while len(uniq) < sz2:
            cand: str = _gen_ip(rng, faker)
            if cand not in seen:
                uniq.append(cand)
                seen.add(cand)
        pools[cid] = uniq
    return pools


def assign_community_ips(
    subgraph: SampledSubgraph | None,
    rng: random.Random,
    faker: Faker,
    n_unique: int = 5000,
) -> dict[str, IpRecord]:
    if subgraph is None or subgraph.nodes.height == 0:
        txids: list[str] = [hashlib.sha256(f"fb:{n_unique}:{i}".encode()).hexdigest() for i in range(5000)]
        cmap: dict[str, int] = {tx: _hi(tx) % 20 for tx in txids}
        counts: Counter[int] = Counter(cmap.values())
        pools: dict[int, list[str]] = _scaled_pools(counts, len(txids), n_unique, rng, faker)
        keys: list[int] = sorted(pools.keys())
        # ensure coverage: assign each pool ip as src to distinct tx
        all_ips: list[str] = [ip for lst in pools.values() for ip in lst]
        result: dict[str, IpRecord] = {}
        for idx, tx in enumerate(txids):
            cid: int = cmap[tx]
            pool: list[str] = pools.get(cid, pools[keys[0]])
            # first n_unique txs get guaranteed unique src
            if idx < len(all_ips):
                src: str = all_ips[idx]
            else:
                src = rng.choice(pool)
            dst: str = rng.choice(pool)
            if src == dst and len(pool) > 1 and rng.random() < 0.9:
                dst = rng.choice(pool)
                while dst == src:
                    dst = rng.choice(pool)
            result[tx] = IpRecord(src, dst, _port(tx, "src"), _port(tx, "dst"), _country_tx(tx), _asn_fb(tx))
        return result

    tx_col: str = subgraph.nodes.columns[0]
    txids2: list[str] = [str(v) for v in subgraph.nodes[tx_col].to_list()]
    cmap2: dict[str, int] = {k: int(v) for k, v in subgraph.communities.items()}
    counts2: Counter[int] = Counter(cmap2.values())
    pools2: dict[int, list[str]] = _scaled_pools(counts2, len(txids2), n_unique, rng, faker)
    keys2: list[int] = sorted(pools2.keys())
    res: dict[str, IpRecord] = {}
    for tx in txids2:
        cid2: int = int(cmap2.get(tx, keys2[0] if keys2 else 0))
        if cid2 not in pools2:
            cid2 = keys2[_hi(tx) % len(keys2)] if keys2 else 0
        pool2: list[str] = pools2[cid2]
        src2: str = rng.choice(pool2)
        dst2: str = rng.choice(pool2)
        if src2 == dst2 and len(pool2) > 1 and rng.random() < 0.9:
            dst2 = rng.choice(pool2)
            while dst2 == src2:
                dst2 = rng.choice(pool2)
        res[tx] = IpRecord(src2, dst2, _port(tx, "src"), _port(tx, "dst"), _country_cid(cid2), _asn(cid2, tx))
    cid_to_txs: dict[int, list[str]] = {}
    for tx in txids2:
        c: int = int(cmap2.get(tx, keys2[0] if keys2 else 0))
        if c not in pools2 and keys2:
            c = keys2[_hi(tx) % len(keys2)]
        cid_to_txs.setdefault(c, []).append(tx)
    pos: dict[int, int] = {c: 0 for c in pools2}
    for cid_pool, lst in pools2.items():
        txs_in_c: list[str] = cid_to_txs.get(cid_pool, [])
        if not txs_in_c:
            txs_in_c = txids2
        for ip in lst:
            tx_target: str = txs_in_c[pos[cid_pool] % len(txs_in_c)]
            pos[cid_pool] += 1
            old: IpRecord = res[tx_target]
            res[tx_target] = IpRecord(ip, old.dst_ip, old.src_port, old.dst_port, old.geo_country, old.geo_asn)
    # ensure >=8 distinct countries (community hash may give <8)
    distinct = {r.geo_country for r in res.values()}
    if len(distinct) < 8:
        missing = [c for c in COUNTRIES if c not in distinct]
        needed: int = 8 - len(distinct)
        tx_list: list[str] = list(res.keys())
        for i in range(needed):
            if i >= len(tx_list) or i >= len(missing):
                break
            tx_m: str = tx_list[i]
            old_m: IpRecord = res[tx_m]
            res[tx_m] = IpRecord(old_m.src_ip, old_m.dst_ip, old_m.src_port, old_m.dst_port, missing[i], old_m.geo_asn)
    return res
