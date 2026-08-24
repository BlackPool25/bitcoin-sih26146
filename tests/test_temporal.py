"""Tests for ml/temporal.py — DAG temporal generator."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime

import polars as pl

from ml.graph_sampler import SampledSubgraph, sample_bfs
from ml.temporal import elliptic_base_time, fit_lambda, generate_timestamps


def _monotonic(ts: list[datetime]) -> bool:
    for i in range(1, len(ts)):
        if not ts[i] > ts[i - 1]:
            return False
    return True


def test_monotonic_within_components() -> None:
    rng = random.Random(42)
    bt = elliptic_base_time(42)
    sub = sample_bfs(None, n=2000, seed=42)
    ts = generate_timestamps(sub, rng, sigma=30, base_time=bt)
    assert len(ts) == sub.nodes.height
    assert _monotonic(ts), "timestamps not strictly monotonic"
    # topo order: every edge must respect time order
    import networkx as nx
    from ml.temporal import _build_dag  # type: ignore[attr-defined]

    dag = _build_dag(sub)  # type: ignore[no-untyped-call]
    # get topo mapping from dag
    topo = list(nx.topological_sort(dag)) if dag.number_of_nodes() > 0 else []
    # need timestamp index mapping
    ts_by_node: dict[str, datetime] = {str(topo[i]): ts[i] for i in range(min(len(topo), len(ts)))}
    # check each edge respects timestamp ordering
    if sub.edges.height > 0:
        c0 = str(sub.edges.columns[0])
        c1 = str(sub.edges.columns[1]) if len(sub.edges.columns) > 1 else c0
        for row in sub.edges.iter_rows(named=True):
            a = str(row[c0])
            b = str(row[c1])
            if a in ts_by_node and b in ts_by_node:
                assert ts_by_node[a] < ts_by_node[b], f"edge {a}->{b} violates topo order"


def test_deterministic() -> None:
    bt = elliptic_base_time(123)
    sub = sample_bfs(None, n=1000, seed=123)
    rng1 = random.Random(999)
    rng2 = random.Random(999)
    ts1 = generate_timestamps(sub, rng1, sigma=30, base_time=bt)
    ts2 = generate_timestamps(sub, rng2, sigma=30, base_time=bt)
    assert ts1 == ts2, "same seed should give identical timestamp lists"
    # also fallback None deterministic
    rng3 = random.Random(777)
    rng4 = random.Random(777)
    bt2 = datetime(2024, 1, 15, tzinfo=UTC)
    ts3 = generate_timestamps(None, rng3, sigma=30, base_time=bt2, n_fallback=500)
    ts4 = generate_timestamps(None, rng4, sigma=30, base_time=bt2, n_fallback=500)
    assert ts3 == ts4


def test_span_30_days_50k() -> None:
    rng = random.Random(42)
    bt = elliptic_base_time(42)
    sub = sample_bfs(None, n=50000, seed=42)
    ts = generate_timestamps(sub, rng, sigma=30, base_time=bt)
    assert len(ts) == 50000
    span = (ts[-1] - ts[0]).total_seconds()
    span_days = span / 86400
    assert span_days >= 30, f"50K span {span_days:.2f} days <30"
    # also fit_lambda check
    lam_empty = fit_lambda([])
    assert abs(lam_empty - 1.0 / 600.0) < 1e-9
    lam_med = fit_lambda([600.0, 600.0, 600.0])
    assert abs(lam_med - 1.0 / 600.0) < 1e-6


def test_cycle_handled() -> None:
    # craft cyclic subgraph: 3 nodes cycle a->b->c->a
    nodes = pl.DataFrame({"txId": ["a", "b", "c"], "time_step": [1, 2, 3]})
    edges = pl.DataFrame({"txId1": ["a", "b", "c"], "txId2": ["b", "c", "a"]})
    sub = SampledSubgraph(nodes=nodes, edges=edges, timesteps=[1, 2, 3], communities={}, injection_plan={})
    rng = random.Random(1)
    bt = datetime(2024, 1, 1, tzinfo=UTC)
    ts = generate_timestamps(sub, rng, sigma=30, base_time=bt)
    assert len(ts) == 3
    assert _monotonic(ts)
    # should have removed at least one edge to break cycle, verify dag is acyclic
    from ml.temporal import _build_dag  # type: ignore[attr-defined]

    dag = _build_dag(sub)
    import networkx as nx

    assert nx.is_directed_acyclic_graph(dag), "dag should be acyclic after cycle removal"


def test_sigma_effect() -> None:
    # sigma 120 should have larger std than sigma 5 for same seed + same topo
    bt = elliptic_base_time(7)
    sub = sample_bfs(None, n=5000, seed=7)
    rng5 = random.Random(2024)
    rng120 = random.Random(2024)
    ts5 = generate_timestamps(sub, rng5, sigma=5, base_time=bt)
    ts120 = generate_timestamps(sub, rng120, sigma=120, base_time=bt)
    assert _monotonic(ts5)
    assert _monotonic(ts120)

    def gaps_std(ts: list[datetime]) -> float:
        gaps: list[float] = []
        for i in range(1, len(ts)):
            gaps.append((ts[i] - ts[i - 1]).total_seconds())
        if len(gaps) < 2:
            return 0.0
        m = sum(gaps) / len(gaps)
        var = sum((x - m) ** 2 for x in gaps) / len(gaps)
        return math.sqrt(var)

    std5 = gaps_std(ts5)
    std120 = gaps_std(ts120)
    assert std120 > std5, f"sigma 120 std {std120:.2f} should exceed sigma 5 std {std5:.2f}"
