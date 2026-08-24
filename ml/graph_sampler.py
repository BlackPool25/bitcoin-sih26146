# allow: SIZE_OK — BFS sampler + injection editing single-file seam
"""ml/graph_sampler.py — BFS sampling + injection subgraph editing."""

from __future__ import annotations

import hashlib
import random
from collections import deque
from dataclasses import dataclass

import networkx as nx
import polars as pl
from typing import Any

from ml.elliptic_loader import EllipticGraph


@dataclass(frozen=True, slots=True)
class SampledSubgraph:
    nodes: pl.DataFrame
    edges: pl.DataFrame
    timesteps: list[int]
    communities: dict[str, int]
    injection_plan: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class InjectionPlan:
    peel_chain: list[str]
    mixer_merge: list[str]
    coinjoin: list[str]
    ransomware: list[str]
    structuring: list[str]
    bridge: list[str]
    high_fee: list[str]
    asn_hop: list[str]

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "peel_chain": list(self.peel_chain),
            "mixer_merge": list(self.mixer_merge),
            "coinjoin": list(self.coinjoin),
            "ransomware": list(self.ransomware),
            "structuring": list(self.structuring),
            "bridge": list(self.bridge),
            "high_fee": list(self.high_fee),
            "asn_hop": list(self.asn_hop),
        }


_KEYS: tuple[str, ...] = (
    "peel_chain",
    "mixer_merge",
    "coinjoin",
    "ransomware",
    "structuring",
    "bridge",
    "high_fee",
    "asn_hop",
)
_RATE: float = 0.04
# peel chain 5-8 hops, mixer merge 3 clusters, coinjoin 22-in/22-out, ransomware fan-out 10-20
_PEEL: tuple[int, int] = (5, 8)
_MIXER: int = 3
_CJ_IN: int = 22
_CJ_OUT: int = 22
_RW_MIN: int = 10
_RW_MAX: int = 20


def _h(s: str, seed: int) -> int:
    return int(hashlib.sha256(f"{seed}:{s}".encode()).hexdigest()[:16], 16)


def _seeds(nodes: list[str], rng: random.Random, k: int = 3) -> list[str]:
    if not nodes:
        return []
    if len(nodes) <= k:
        return list(nodes)
    return rng.sample(nodes, k)


def _digraph(tx: list[str], edges: pl.DataFrame) -> nx.DiGraph[Any, Any]:
    g: nx.DiGraph[Any, Any] = nx.DiGraph()
    for t in tx:
        g.add_node(t)
    if edges.height == 0:
        return g
    c0 = edges.columns[0]
    c1 = edges.columns[1] if len(edges.columns) > 1 else c0
    s: set[str] = set(tx)
    for r in edges.iter_rows(named=True):
        a = str(r[c0])
        b = str(r[c1])
        if a in s and b in s and a != b:
            g.add_edge(a, b)
    return g


def _bfs(g: nx.DiGraph[Any, Any], seeds: list[str], n: int, rng: random.Random) -> set[str]:
    if n <= 0:
        return set()
    if not seeds:
        al: list[str] = list(g.nodes())
        if not al:
            return set()
        seeds = [rng.choice(al)]
    vis: set[str] = set(seeds)
    q: deque[str] = deque(seeds)
    while q and len(vis) < n:
        cur = q.popleft()
        if cur not in g:
            continue
        succ: list[str] = sorted(g.successors(cur))
        pred: list[str] = sorted(g.predecessors(cur))
        neigh: list[str] = succ + [p for p in pred if p not in succ]
        if len(neigh) > 1:
            rng.shuffle(neigh)
        for nb in neigh:
            if nb not in vis:
                vis.add(nb)
                q.append(nb)
                if len(vis) >= n:
                    break
    if len(vis) < n:
        rem: list[str] = [x for x in g.nodes() if x not in vis]
        rng.shuffle(rem)
        for x in rem:
            vis.add(x)
            if len(vis) >= n:
                break
    if len(vis) > n:
        lst: list[str] = list(seeds)
        extra: list[str] = [x for x in vis if x not in set(lst)]
        rng.shuffle(extra)
        vis = set(lst + extra[: max(0, n - len(lst))])
        if len(vis) > n:
            vis = set(list(vis)[:n])
    return vis


def _cut(edges: pl.DataFrame, keep: set[str]) -> pl.DataFrame:
    if edges.height == 0 or not keep:
        return edges.clear()
    c0 = edges.columns[0]
    c1 = edges.columns[1] if len(edges.columns) > 1 else c0
    return edges.filter(
        pl.col(c0).cast(pl.Utf8).is_in(list(keep))
        & pl.col(c1).cast(pl.Utf8).is_in(list(keep))
    )


def _weak(g: nx.DiGraph[Any, Any], vis: set[str], rng: random.Random) -> set[str]:
    if len(vis) <= 1:
        return vis
    sub: nx.DiGraph[Any, Any] = g.subgraph(vis).copy()  # type: ignore[assignment]
    comps: list[set[str]] = [set(c) for c in nx.weakly_connected_components(sub)]
    if len(comps) <= 3:
        return vis
    comps.sort(key=len, reverse=True)
    keep: set[str] = set().union(*comps[:3])
    cand: set[str] = set()
    for nd in keep:
        cand.update(g.successors(nd))
        cand.update(g.predecessors(nd))
    cand -= keep
    cand -= vis
    cl: list[str] = sorted(cand)
    rng.shuffle(cl)
    out: set[str] = set(keep)
    for c in cl:
        if len(out) >= len(vis):
            break
        out.add(c)
    if len(out) < len(vis):
        rem: list[str] = [x for x in g.nodes() if x not in out]
        rng.shuffle(rem)
        for r in rem:
            out.add(r)
            if len(out) >= len(vis):
                break
    return out


def _acyc(g: nx.DiGraph[Any, Any]) -> nx.DiGraph[Any, Any]:
    cur: nx.DiGraph[Any, Any] = g.copy()  # type: ignore[assignment]
    lim: int = cur.number_of_edges() + 5
    it: int = 0
    while not nx.is_directed_acyclic_graph(cur) and it < lim:
        try:
            cyc: list[tuple[str, str]] = nx.find_cycle(cur)
        except nx.NetworkXNoCycle:
            break
        best: tuple[str, str] | None = None
        bw: int | None = None
        for u, v in cyc:
            w = _h(f"{u}->{v}", 0)
            if bw is None or w < bw:
                bw = w
                best = (u, v)
        if best is not None and cur.has_edge(best[0], best[1]):
            cur.remove_edge(best[0], best[1])
        it += 1
    return cur


def _comm(tx: list[str], seed: int, k: int = 7) -> dict[str, int]:
    return {t: int(_h(t, seed) % k) for t in tx}


def _plan(tx: list[str], rate: float, seed: int) -> dict[str, list[str]]:
    n: int = len(tx)
    if n == 0:
        return {key: [] for key in _KEYS}
    per: int = max(1, int(round(rate * float(n) / float(len(_KEYS)))))
    tot: int = per * len(_KEYS)
    if tot > n:
        per = max(1, n // len(_KEYS))
    rng = random.Random(seed)
    sh: list[str] = list(tx)
    rng.shuffle(sh)
    out: dict[str, list[str]] = {}
    idx: int = 0
    for key in _KEYS:
        out[key] = list(sh[idx : idx + per])
        idx += per
    return out


def _fallback(n: int, seed: int) -> SampledSubgraph:
    rng = random.Random(seed)
    tx: list[str] = [f"tx_synth_{hashlib.sha256(f'{seed}:{i}:tx'.encode()).hexdigest()[:16]}" for i in range(n)]
    raw: list[int] = [(_h(t, seed) % 49) + 1 for t in tx]
    paired: list[tuple[str, int]] = sorted(zip(tx, raw, strict=True), key=lambda x: x[1])
    stx: list[str] = [p[0] for p in paired]
    sts: list[int] = sorted([p[1] for p in paired])
    nodes: pl.DataFrame = pl.DataFrame({"txId": stx, "time_step": sts})
    src: list[str] = []
    dst: list[str] = []
    for i in range(n - 1):
        src.append(stx[i])
        dst.append(stx[i + 1])
    for i in range(n):
        if rng.random() < 0.12 and i + 2 < n:
            j = rng.randint(i + 2, min(n - 1, i + 10))
            src.append(stx[i])
            dst.append(stx[j])
    edges: pl.DataFrame = pl.DataFrame({"txId1": src, "txId2": dst})
    return SampledSubgraph(
        nodes=nodes,
        edges=edges,
        timesteps=sorted(set(sts)),
        communities=_comm(stx, seed),
        injection_plan=_plan(stx, _RATE, seed),
    )


def plan_injections(subgraph: SampledSubgraph, rate: float = 0.04, seed: int = 42) -> dict[str, list[str]]:
    col = subgraph.nodes.columns[0] if subgraph.nodes.height > 0 else "txId"
    ids: list[str] = subgraph.nodes[col].to_list() if subgraph.nodes.height > 0 else []
    return _plan(ids, rate, seed)


def sample_bfs(graph: EllipticGraph | None, n: int = 50000, seed: int = 42) -> SampledSubgraph:
    if graph is None or graph.nodes.height == 0:
        return _fallback(n, seed)
    tx_col: str = graph.nodes.columns[0]
    all_tx: list[str] = [str(x) for x in graph.nodes[tx_col].to_list()]
    if n >= len(all_tx):
        keep: set[str] = set(all_tx)
        ef = _cut(graph.edges, keep)
        ts_all: dict[str, int] = {all_tx[i]: int(graph.timesteps[i]) for i in range(len(all_tx))}
        if ef.height > 0:
            c0a = ef.columns[0]
            c1a = ef.columns[1] if len(ef.columns) > 1 else c0a
            keep_rows: list[dict[str, str]] = []
            for r in ef.iter_rows(named=True):
                a = str(r[c0a])
                b = str(r[c1a])
                if ts_all.get(a, 0) <= ts_all.get(b, 0):
                    keep_rows.append({c0a: a, c1a: b})
            if len(keep_rows) != ef.height:
                ef = pl.DataFrame(keep_rows) if keep_rows else ef.clear()
        gs = _acyc(_digraph(all_tx, ef))
        if gs.number_of_edges() > 0:
            s: list[str] = []
            d: list[str] = []
            for u, v in gs.edges():
                s.append(str(u))
                d.append(str(v))
            ef2: pl.DataFrame = pl.DataFrame({"txId1": s, "txId2": d})
        else:
            ef2 = ef.clear()
        uniq: list[int] = sorted(set(int(v) for v in graph.timesteps.tolist()))
        return SampledSubgraph(
            nodes=graph.nodes,
            edges=ef2,
            timesteps=uniq,
            communities=_comm(all_tx, seed),
            injection_plan=_plan(all_tx, _RATE, seed),
        )
    rng = random.Random(seed)
    ill: list[str] = [str(all_tx[i]) for i in range(len(all_tx)) if int(graph.labels[i]) == 1]
    seeds: list[str] = _seeds(ill, rng, 3)
    if not seeds:
        tmp: list[str] = list(all_tx)
        rng.shuffle(tmp)
        seeds = tmp[: min(3, len(tmp))]
    g2: nx.DiGraph[Any, Any] = _digraph(all_tx, graph.edges)
    # Filter seeds to those actually in g2 (isolated illicit may not be in edge graph but should still be in node set — ensure they are)
    seeds = [s for s in seeds if s in g2]
    if not seeds:
        # fallback: pick any node present in g2
        tmp2: list[str] = list(g2.nodes())
        rng.shuffle(tmp2)
        seeds = tmp2[: min(3, len(tmp2))]
    vis: set[str] = _bfs(g2, seeds, n, rng)
    vis = _weak(g2, vis, rng)
    if len(vis) > n:
        lst: list[str] = list(vis)
        rng.shuffle(lst)
        keep2: set[str] = set(seeds)
        for v in lst:
            if len(keep2) >= n:
                break
            keep2.add(v)
        vis = keep2
    elif len(vis) < n:
        rem: list[str] = [x for x in all_tx if x not in vis]
        rng.shuffle(rem)
        for r in rem:
            vis.add(r)
            if len(vis) >= n:
                break
    ef3 = _cut(graph.edges, vis)
    ts_map: dict[str, int] = {all_tx[i]: int(graph.timesteps[i]) for i in range(len(all_tx))}
    if ef3.height > 0:
        c0b = ef3.columns[0]
        c1b = ef3.columns[1] if len(ef3.columns) > 1 else c0b
        frows: list[dict[str, str]] = []
        for r in ef3.iter_rows(named=True):
            a = str(r[c0b])
            b = str(r[c1b])
            if ts_map.get(a, 0) <= ts_map.get(b, 0):
                frows.append({c0b: a, c1b: b})
        if len(frows) != ef3.height:
            ef3 = pl.DataFrame(frows) if frows else ef3.clear()
    gs3 = _acyc(_digraph(list(vis), ef3))
    if gs3.number_of_edges() > 0:
        s3: list[str] = []
        d3: list[str] = []
        for u, v in gs3.edges():
            s3.append(str(u))
            d3.append(str(v))
        ef4: pl.DataFrame = pl.DataFrame({"txId1": s3, "txId2": d3})
    else:
        ef4 = ef3.clear()
    nodes_f: pl.DataFrame = graph.nodes.filter(pl.col(tx_col).cast(pl.Utf8).is_in(list(vis)))
    idx_map: dict[str, int] = {tx: i for i, tx in enumerate(all_tx)}
    s_ts: list[int] = [int(graph.timesteps[idx_map[t]]) for t in vis if t in idx_map]
    uniq2: list[int] = sorted(set(s_ts))
    return SampledSubgraph(
        nodes=nodes_f,
        edges=ef4,
        timesteps=uniq2,
        communities=_comm(list(vis), seed),
        injection_plan=_plan(list(vis), _RATE, seed),
    )
