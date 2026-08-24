"""Tests for ml/graph_sampler.py — BFS sampling + injection editing."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

FIXTURE = Path("tests/fixtures/elliptic_mini")


def _tx_set(df) -> set[str]:  # type: ignore[no-untyped-def]
    col = df.columns[0]
    return set(df[col].to_list())


def test_seed_determinism() -> None:
    from ml.elliptic_loader import load_elliptic
    from ml.graph_sampler import sample_bfs

    g = load_elliptic(FIXTURE)
    assert g is not None
    a = sample_bfs(g, n=8, seed=42)
    b = sample_bfs(g, n=8, seed=42)
    assert _tx_set(a.nodes) == _tx_set(b.nodes), "same seed must give same txid sets"
    assert _tx_set(a.nodes) != set()
    # fallback determinism
    fa = sample_bfs(None, n=50, seed=123)
    fb = sample_bfs(None, n=50, seed=123)
    assert _tx_set(fa.nodes) == _tx_set(fb.nodes)
    # different seed should differ (probabilistic)
    fc = sample_bfs(None, n=50, seed=999)
    assert _tx_set(fa.nodes) != _tx_set(fc.nodes)


def test_connectivity_weakly_connected() -> None:
    from ml.elliptic_loader import load_elliptic
    from ml.graph_sampler import sample_bfs

    g = load_elliptic(FIXTURE)
    assert g is not None
    sub = sample_bfs(g, n=8, seed=7)
    # build DiGraph from sampled edges
    dg: nx.DiGraph[str] = nx.DiGraph()  # type: ignore[type-arg]
    for tx in _tx_set(sub.nodes):
        dg.add_node(tx)
    if sub.edges.height > 0:
        c0 = sub.edges.columns[0]
        c1 = sub.edges.columns[1]
        for r in sub.edges.iter_rows(named=True):
            dg.add_edge(str(r[c0]), str(r[c1]))
    # weakly connected ≤3
    comps = list(nx.weakly_connected_components(dg))
    assert len(comps) <= 3, f"weakly components {len(comps)} >3"
    # fallback also weakly connected
    fb = sample_bfs(None, n=100, seed=42)
    dg2: nx.DiGraph[str] = nx.DiGraph()  # type: ignore[type-arg]
    for tx in _tx_set(fb.nodes):
        dg2.add_node(tx)
    if fb.edges.height > 0:
        c0 = fb.edges.columns[0]
        c1 = fb.edges.columns[1]
        for r in fb.edges.iter_rows(named=True):
            dg2.add_edge(str(r[c0]), str(r[c1]))
    comps2 = list(nx.weakly_connected_components(dg2))
    assert len(comps2) <= 3


def test_timestep_monotonicity() -> None:
    from ml.elliptic_loader import load_elliptic
    from ml.graph_sampler import sample_bfs

    g = load_elliptic(FIXTURE)
    assert g is not None
    sub = sample_bfs(g, n=5, seed=42)
    assert sub.timesteps == sorted(sub.timesteps), "timesteps must be sorted"
    assert all(1 <= int(v) <= 49 for v in sub.timesteps)
    # fallback monotonic
    fb = sample_bfs(None, n=200, seed=42)
    assert fb.timesteps == sorted(fb.timesteps)
    assert all(1 <= int(v) <= 49 for v in fb.timesteps)


def test_no_cycle() -> None:
    from ml.elliptic_loader import load_elliptic
    from ml.graph_sampler import sample_bfs

    g = load_elliptic(FIXTURE)
    assert g is not None
    sub = sample_bfs(g, n=10, seed=42)
    dg: nx.DiGraph[str] = nx.DiGraph()  # type: ignore[type-arg]
    for tx in _tx_set(sub.nodes):
        dg.add_node(tx)
    if sub.edges.height > 0:
        c0 = sub.edges.columns[0]
        c1 = sub.edges.columns[1]
        for r in sub.edges.iter_rows(named=True):
            dg.add_edge(str(r[c0]), str(r[c1]))
    assert nx.is_directed_acyclic_graph(dg), "sampled subgraph must be acyclic"
    # fallback acyclic
    fb = sample_bfs(None, n=100, seed=42)
    dg2: nx.DiGraph[str] = nx.DiGraph()  # type: ignore[type-arg]
    for tx in _tx_set(fb.nodes):
        dg2.add_node(tx)
    if fb.edges.height > 0:
        c0 = fb.edges.columns[0]
        c1 = fb.edges.columns[1]
        for r in fb.edges.iter_rows(named=True):
            dg2.add_edge(str(r[c0]), str(r[c1]))
    assert nx.is_directed_acyclic_graph(dg2)


def test_plan_injections_counts() -> None:
    from ml.graph_sampler import plan_injections, sample_bfs

    # large fallback 50K to check 250±50 per label at 4% rate
    sub = sample_bfs(None, n=50000, seed=42)
    plan = plan_injections(sub, rate=0.04)
    assert isinstance(plan, dict)
    # expect 8 keys
    assert len(plan) == 8
    for key, lst in plan.items():
        assert 200 <= len(lst) <= 300, f"{key} {len(lst)} not in 250±50"
    total = sum(len(v) for v in plan.values())
    assert 1900 <= total <= 2100, f"total {total} not in 2000±100"
    # small n tolerance still passes
    small = sample_bfs(None, n=1000, seed=7)
    p2 = plan_injections(small, rate=0.04)
    for lst in p2.values():
        assert len(lst) >= 1
    # check injection_plan embedded in subgraph
    assert isinstance(sub.injection_plan, dict)
    assert len(sub.injection_plan) == 8
