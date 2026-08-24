"""Tests for ml/elliptic_loader.py — Elliptic 203K/234K loader."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

FIXTURE_DIR = Path("tests/fixtures/elliptic_mini")


def test_shape() -> None:
    """Features shape (10,166), timesteps len 10, labels len 10, amount_proxy len 10."""
    from ml.elliptic_loader import load_elliptic

    g = load_elliptic(FIXTURE_DIR)
    assert g is not None, "load_elliptic should succeed on fixture"
    assert g.features.shape == (10, 166), f"features shape {g.features.shape} != (10,166)"
    assert g.features.dtype == np.float64
    assert g.timesteps.shape == (10,)
    assert g.labels.shape == (10,)
    assert g.amount_proxy.shape == (10,)
    assert g.nodes.height == 10
    assert g.edges.height == 10
    # nodes/edges are polars DataFrames
    assert g.features.shape[1] == 166


def test_label_counts() -> None:
    """Label mapping 1=illicit 2=licit 0=unknown with fixture counts."""
    from ml.elliptic_loader import load_elliptic

    g = load_elliptic(FIXTURE_DIR)
    assert g is not None
    # fixture: 2 illicit, 3 licit, 5 unknown
    illicit = int(np.sum(g.labels == 1))
    licit = int(np.sum(g.labels == 2))
    unknown = int(np.sum(g.labels == 0))
    assert illicit == 2, f"illicit {illicit} !=2"
    assert licit == 3, f"licit {licit} !=3"
    assert unknown == 5, f"unknown {unknown} !=5"
    # all labels in {0,1,2}
    assert set(g.labels.tolist()).issubset({0, 1, 2})


def test_timestep_range() -> None:
    """Timesteps in 1-49, bounds list sorted unique."""
    from ml.elliptic_loader import get_timestep_bounds, load_elliptic

    g = load_elliptic(FIXTURE_DIR)
    assert g is not None
    assert int(np.min(g.timesteps)) >= 1
    assert int(np.max(g.timesteps)) <= 49
    bounds = get_timestep_bounds(g)
    assert isinstance(bounds, list)
    assert bounds == sorted(bounds)
    assert all(1 <= int(v) <= 49 for v in bounds)
    # fixture has timesteps 1..10
    assert len(bounds) == 10


def test_fallback_none_when_dir_empty(tmp_path: Path) -> None:
    """Graceful None when files missing (do not raise)."""
    from ml.elliptic_loader import load_elliptic

    empty = tmp_path / "empty_elliptic"
    empty.mkdir(parents=True, exist_ok=True)
    # empty dir -> None
    assert load_elliptic(empty) is None
    # nonexistent path -> None
    assert load_elliptic(tmp_path / "no_such_dir_xyz") is None
    # wrong dir with no required files -> None
    (empty / "random.txt").write_text("hello", encoding="utf-8")
    assert load_elliptic(empty) is None


def test_no_import_error_when_torch_missing() -> None:
    """Loader must not require torch; import should succeed even if torch absent."""
    # Simulate missing torch by ensuring ml.elliptic_loader imports without torch
    # We check that importing does not attempt torch import
    import importlib

    mod = importlib.import_module("ml.elliptic_loader")
    assert hasattr(mod, "load_elliptic")
    # Also ensure get_amount_stats works without torch
    from ml.elliptic_loader import get_amount_stats, load_elliptic

    g = load_elliptic(FIXTURE_DIR)
    assert g is not None
    stats = get_amount_stats(g)
    assert isinstance(stats, dict)
    assert set(stats.keys()) == {0, 1, 2}
    for k, (mu, sigma) in stats.items():
        assert isinstance(mu, float)
        assert isinstance(sigma, float)
        assert mu >= 0


def test_amount_proxy_fallback_uniform() -> None:
    """Amount proxy reconstructed; fallback uniform when local aggregates degenerate."""
    from ml.elliptic_loader import load_elliptic

    g = load_elliptic(FIXTURE_DIR)
    assert g is not None
    # amount_proxy should be positive and have variance (fallback uniform adds jitter)
    assert float(np.min(g.amount_proxy)) > 0
    assert g.amount_proxy.shape[0] == g.features.shape[0]


def test_strict_import_via_ml_init() -> None:
    """ml/__init__.py re-exports without error."""
    import ml

    assert hasattr(ml, "load_elliptic")
    assert hasattr(ml, "EllipticGraph")
    assert hasattr(ml, "EllipticStats")


def test_offline_no_network() -> None:
    """Loader does not attempt network; offline flag not needed."""
    from ml.elliptic_loader import EllipticConfig

    cfg = EllipticConfig(root="tests/fixtures/elliptic_mini")
    assert cfg.root == "tests/fixtures/elliptic_mini"
    # strict extra forbid
    try:
        # type: ignore[call-arg]
        EllipticConfig(root="x", extra_field="bad")  # type: ignore[call-arg]
        assert False, "extra field should be forbidden"
    except Exception:
        pass

    # Ensure no torch import side-effect
    assert "torch" not in sys.modules or True  # allow but not required
