"""ml/temporal.py — DAG-aware temporal generator with topo-sort + Exp(λ) + sigma jitter."""

from __future__ import annotations

import hashlib
import math
import random
from datetime import UTC, datetime, timedelta

import networkx as nx

from ml.graph_sampler import SampledSubgraph

_DEFAULT_GAP: float = 600.0
_DEFAULT_LAMBDA: float = 1.0 / 600.0
_ELLIPTIC_EPOCH: datetime = datetime(2024, 1, 1, tzinfo=UTC)
_FALLBACK_N: int = 50000
_MIN_GAP_SEC: float = 0.001


def fit_lambda(timestep_gaps: list[float]) -> float:
    """Fit λ as 1 / median(gap). Falls back to 1/600 when gaps empty or median ≤0."""
    if not timestep_gaps:
        return _DEFAULT_LAMBDA
    filtered: list[float] = [float(g) for g in timestep_gaps if float(g) > 0]
    if not filtered:
        return _DEFAULT_LAMBDA
    s: list[float] = sorted(filtered)
    n: int = len(s)
    mid: int = n // 2
    if n % 2 == 1:
        median: float = float(s[mid])
    else:
        median = float((s[mid - 1] + s[mid]) / 2.0)
    if median <= 0:
        return _DEFAULT_LAMBDA
    return 1.0 / median


def elliptic_base_time(seed: int) -> datetime:
    """Deterministic base time for elliptic-anchored runs: 2024-01-01 + seed%30 days."""
    offset: int = int(seed % 30)
    return _ELLIPTIC_EPOCH + timedelta(days=offset)


def _hash_edge(u: str, v: str, seed: int = 0) -> int:
    raw: str = f"{seed}:{u}->{v}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _build_dag(subgraph: SampledSubgraph) -> nx.DiGraph[str]:
    g: nx.DiGraph[str] = nx.DiGraph()
    # nodes: first column is txId
    if subgraph.nodes.height > 0:
        tx_col: str = str(subgraph.nodes.columns[0])
        for tx in subgraph.nodes[tx_col].to_list():
            g.add_node(str(tx))
    else:
        return g
    if subgraph.edges.height == 0:
        return g
    c0: str = str(subgraph.edges.columns[0])
    c1: str = str(subgraph.edges.columns[1]) if len(subgraph.edges.columns) > 1 else c0
    # keep set for fast membership
    keep: set[str] = set(str(n) for n in g.nodes())
    for row in subgraph.edges.iter_rows(named=True):
        a: str = str(row[c0])
        b: str = str(row[c1])
        if a in keep and b in keep and a != b:
            g.add_edge(a, b)
    # break cycles by removing smallest-hash edge in each cycle
    limit: int = g.number_of_edges() + 5
    it: int = 0
    while not nx.is_directed_acyclic_graph(g) and it < limit:
        try:
            cycle: list[tuple[str, str]] = list(nx.find_cycle(g))
        except nx.NetworkXNoCycle:
            break
        best: tuple[str, str] | None = None
        best_w: int | None = None
        for u, v in cycle:
            w: int = _hash_edge(str(u), str(v), 0)
            if best_w is None or w < best_w:
                best_w = w
                best = (str(u), str(v))
        if best is not None and g.has_edge(best[0], best[1]):
            g.remove_edge(best[0], best[1])
        it += 1
    return g


def generate_timestamps(
    subgraph: SampledSubgraph | None,
    rng: random.Random,
    sigma: int,
    base_time: datetime,
    *,
    n_fallback: int | None = None,
) -> list[datetime]:
    """Generate monotonic DAG-respecting timestamps.

    topo sort list(nx.topological_sort(dag)) on sampled edges, if cycle remove
    smallest-hash edges until DAG, walk topo order t[0]=base_time,
    t[i]=t[i-1]+Exp(λ) via -ln(U)/λ + gauss(0,sigma) jitter, clamp gap>0.
    sigma 5 tight, 120 loose, all monotonic.
    When subgraph is None fallback: base_time + i*600 + gauss, clamped monotonic.
    Deterministic for same rng seed.
    """
    lam: float = _DEFAULT_LAMBDA
    # fallback path
    if subgraph is None or subgraph.nodes.height == 0:
        n: int = int(n_fallback) if n_fallback is not None else _FALLBACK_N
        # ensure tz-aware
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=UTC)
        out: list[datetime] = []
        prev: datetime = base_time
        for i in range(n):
            if i == 0:
                jitter: float = rng.gauss(0, float(sigma))
                # clamp first jitter so we don't go far backward
                cur: datetime = base_time + timedelta(seconds=float(jitter))
                # ensure at least base_time if jitter negative large? Keep monotonic from base_time
                if cur < base_time:
                    # bring forward minimally
                    cur = base_time + timedelta(microseconds=1)
                prev = cur
                out.append(cur)
            else:
                raw: datetime = base_time + timedelta(seconds=float(i) * _DEFAULT_GAP + rng.gauss(0, float(sigma)))
                # clamp to ensure monotonic
                if raw <= prev:
                    raw = prev + timedelta(seconds=_MIN_GAP_SEC)
                prev = raw
                out.append(raw)
        return out

    # build DAG and compute lambda from timesteps
    dag: nx.DiGraph[str] = _build_dag(subgraph)
    # derive gaps for lambda: scale integer step diffs to seconds
    gaps: list[float] = []
    if len(subgraph.timesteps) > 1:
        st: list[int] = sorted(int(v) for v in subgraph.timesteps)
        for idx in range(1, len(st)):
            diff: int = int(st[idx] - st[idx - 1])
            if diff > 0:
                gaps.append(float(diff) * _DEFAULT_GAP)
    if gaps:
        lam = fit_lambda(gaps)
    else:
        lam = _DEFAULT_LAMBDA

    # ensure dag contains all nodes (isolated included)
    tx_col2: str = str(subgraph.nodes.columns[0])
    all_tx: list[str] = [str(v) for v in subgraph.nodes[tx_col2].to_list()]
    for tx in all_tx:
        if tx not in dag:
            dag.add_node(tx)

    # topo order
    try:
        order: list[str] = list(nx.topological_sort(dag))
    except nx.NetworkXUnfeasible:
        # fallback: should not happen because we broke cycles, but handle
        order = list(all_tx)
        # try to remove remaining cycle edges again
        dag2: nx.DiGraph[str] = _build_dag(subgraph)
        with __import__("contextlib").suppress(Exception):
            order = list(nx.topological_sort(dag2))
            if len(order) != len(all_tx):
                # append missing
                missing: list[str] = [t for t in all_tx if t not in set(order)]
                order.extend(missing)

    # walk topo order
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=UTC)

    ts_map: dict[str, datetime] = {}
    prev_dt: datetime = base_time
    for idx, node in enumerate(order):
        if idx == 0:
            cur2: datetime = base_time
        else:
            u: float = rng.random()
            if u <= 0.0:
                u = 1e-12
            if u >= 1.0:
                u = 1 - 1e-12
            exp_gap: float = -math.log(u) / lam if lam > 0 else _DEFAULT_GAP
            # fallback to expovariate if math fails
            # jitter
            jitter2: float = rng.gauss(0, float(sigma))
            gap: float = float(exp_gap) + float(jitter2)
            if gap <= _MIN_GAP_SEC:
                gap = _MIN_GAP_SEC
            cur2 = prev_dt + timedelta(seconds=float(gap))
            prev_dt = cur2
        ts_map[str(node)] = cur2

    # return in topo order
    result: list[datetime] = [ts_map[str(n)] for n in order]
    return result


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(description="DAG temporal generator")
    p.add_argument("--sigma", type=int, choices=[5, 30, 120], default=30, help="jitter sigma seconds")
    p.add_argument("--seed", type=int, default=42, help="rng seed")
    p.add_argument("--n", type=int, default=1000, help="fallback n when no elliptic data")
    args = p.parse_args()
    rng = random.Random(int(args.seed))
    bt: datetime = elliptic_base_time(int(args.seed))
    from ml.graph_sampler import sample_bfs

    sub = sample_bfs(None, n=int(args.n), seed=int(args.seed))
    ts: list[datetime] = generate_timestamps(sub, rng, int(args.sigma), bt)
    span_days: float = (ts[-1] - ts[0]).total_seconds() / 86400 if len(ts) > 1 else 0.0
    print(f"generated {len(ts)} timestamps sigma={args.sigma} seed={args.seed} base={bt.isoformat()} span_days={span_days:.2f}")
    for t in ts[:3]:
        print(t.isoformat())


if __name__ == "__main__":
    _cli()
