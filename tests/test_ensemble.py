"""TDD RED tests for T05 ml/ensemble.py — fuse 0.4*sigmoid(IF)+0.6*softmax(GNN) hedge."""

from __future__ import annotations

import re
from pathlib import Path

ENSEMBLE_PY = Path("ml/ensemble.py")


def test_fuse_weights() -> None:
    """fuse(0.6,0.8)==0.72 with 0.4/0.6 weighting."""
    from ml.ensemble import fuse  # type: ignore[import-untyped]

    result = fuse(0.6, 0.8)
    val = float(result)  # type: ignore[arg-type]
    assert abs(val - 0.72) < 1e-9, f"fuse(0.6,0.8)={val} !=0.72"


def test_softmax_used() -> None:
    """grep softmax — GNN branch must use softmax."""
    assert ENSEMBLE_PY.exists(), f"{ENSEMBLE_PY} missing — implement ml/ensemble.py"
    text = ENSEMBLE_PY.read_text(encoding="utf-8")
    assert "softmax" in text.lower(), "softmax not found in ml/ensemble.py — GNN must use softmax"


def test_weights_0_4_0_6() -> None:
    """grep 0.4 and 0.6 — fusion weights."""
    assert ENSEMBLE_PY.exists(), f"{ENSEMBLE_PY} missing"
    text = ENSEMBLE_PY.read_text(encoding="utf-8")
    assert "0.4" in text, "0.4 not found in ml/ensemble.py"
    assert "0.6" in text, "0.6 not found in ml/ensemble.py"


def test_xgb_hedge_ref() -> None:
    """grep 0.669 — XGB SOTA hedge reference."""
    assert ENSEMBLE_PY.exists(), f"{ENSEMBLE_PY} missing"
    text = ENSEMBLE_PY.read_text(encoding="utf-8")
    assert "0.669" in text, "0.669 not found in ml/ensemble.py — XGB_SOTA hedge missing"


def test_no_fake_5pp() -> None:
    """grep beats.*5pp should be 0 — no fake 5pp claim."""
    assert ENSEMBLE_PY.exists(), f"{ENSEMBLE_PY} missing"
    text = ENSEMBLE_PY.read_text(encoding="utf-8")
    hits = re.findall(r"beats.*5pp", text, flags=re.IGNORECASE)
    assert len(hits) == 0, f"fake 5pp claim found in ml/ensemble.py: {hits}"
