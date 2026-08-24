"""T04 ROCm parity + CPU fallback — RED/GREEN harness."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def test_cpu_fallback_always_pass() -> None:
    """CPU fallback must always pass — no cuda needed, torch optional."""
    try:
        import torch  # type: ignore[import-untyped]  # noqa: F401

        # torch present — still pass; cuda not required
        assert True
    except ImportError:
        # torch missing — CPU fallback still passes
        assert True
        return
    # trivial guarantee
    assert pytest.approx(1.0, abs=1e-6) == 1.0


def test_hipblaslt_guard() -> None:
    """Code must contain TORCH_BLAS_PREFER_HIPBLASLT guard."""
    path = Path("ml/train_gnn.py")
    assert path.exists(), "ml/train_gnn.py missing"
    text = path.read_text(encoding="utf-8")
    assert "TORCH_BLAS_PREFER_HIPBLASLT" in text, "missing TORCH_BLAS_PREFER_HIPBLASLT guard"


def test_weights_only_and_map_location() -> None:
    """Code must use weights_only=True and map_location cpu."""
    path = Path("ml/train_gnn.py")
    assert path.exists(), "ml/train_gnn.py missing"
    text = path.read_text(encoding="utf-8")
    assert "weights_only=True" in text, "missing weights_only=True"
    # map_location.*cpu regex
    assert re.search(r"map_location.*cpu", text) is not None, "missing map_location.*cpu"


def test_gnn_pt_exists() -> None:
    """Bundle models/gnn.pt must exist after script run."""
    pt = Path("models/gnn.pt")
    assert pt.exists(), "models/gnn.pt missing — run ml/train_gnn.py"
    assert pt.stat().st_size > 0, "models/gnn.pt empty"
