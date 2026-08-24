"""TDD RED tests for T03 ml/train.py — IsolationForest contamination 0.02 n_estimators 200."""

from __future__ import annotations

import pickle
import re
import time
from pathlib import Path

import numpy as np

TRAIN_PY = Path("ml/train.py")
IF_PKL = Path("models/if.pkl")
FEATURES_PARQUET = Path("data/features/features.parquet")


def test_if_train_time() -> None:
    """fit on 50Kx38 wall time <5s (max_samples 256 keeps O(n log n) cheap)."""
    from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

    rng = np.random.default_rng(42)
    X = rng.standard_normal((50000, 38)).astype(np.float64)
    clf = IsolationForest(  # type: ignore[call-arg]
        contamination=0.02,  # type: ignore[arg-type]
        n_estimators=200,
        max_samples=256,  # type: ignore[arg-type]
        max_features=1.0,
        bootstrap=False,
        n_jobs=-1,
        random_state=42,
    )
    t0 = time.perf_counter()
    clf.fit(X)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"IF train time {elapsed:.2f}s >=5s — max_samples 256 must keep <5s"


def test_if_params() -> None:
    """IsolationForest params: contamination 0.02, n_estimators 200, max_samples 256."""
    assert TRAIN_PY.exists(), f"{TRAIN_PY} missing — implement ml/train.py"
    text = TRAIN_PY.read_text(encoding="utf-8")
    # grep params as literals
    assert "contamination=0.02" in text or "contamination = 0.02" in text, (
        "contamination 0.02 not found in ml/train.py"
    )
    assert "n_estimators=200" in text or "n_estimators = 200" in text, "n_estimators 200 not found"
    assert "max_samples=256" in text or "max_samples = 256" in text, "max_samples 256 not found"
    # also load real pkl if exists and verify params
    if IF_PKL.exists():
        m = pickle.loads(IF_PKL.read_bytes())
        # m is IsolationForest
        assert hasattr(m, "contamination"), "if.pkl missing contamination attr"
        assert float(m.contamination) == 0.02, f"contamination {m.contamination} !=0.02"
        assert int(m.n_estimators) == 200, f"n_estimators {m.n_estimators} !=200"
        assert int(m.max_samples) == 256, f"max_samples {m.max_samples} !=256"


def test_score_samples_used() -> None:
    """grep score_samples >=1 and decision_function ==0 for prob (not used for prob)."""
    assert TRAIN_PY.exists(), f"{TRAIN_PY} missing"
    text = TRAIN_PY.read_text(encoding="utf-8")
    score_hits = len(re.findall(r"score_samples", text))
    assert score_hits >= 1, f"score_samples not found in ml/train.py (hits={score_hits})"
    # decision_function must NOT be used to compute prob — allow offset_ usage but not prob
    # Strict: count decision_function occurrences — must be 0 OR only offset_ related not prob
    df_hits = len(re.findall(r"decision_function", text))
    # If decision_function appears, ensure it's not in prob computation context
    assert df_hits == 0, (
        f"decision_function found {df_hits} times — must use score_samples for prob"
    )


def test_if_pkl_exists() -> None:
    """models/if.pkl exists, <5MB, loadable, contamination 0.02."""
    assert IF_PKL.exists(), f"{IF_PKL} not found — run ml/train.py"
    size = IF_PKL.stat().st_size
    assert size > 0, "if.pkl empty"
    assert size < 5 * 1024 * 1024, f"if.pkl {size} bytes >=5MB"
    m = pickle.loads(IF_PKL.read_bytes())
    assert hasattr(m, "contamination")
    assert float(m.contamination) == 0.02, f"contamination {m.contamination} !=0.02"
    # check n_estimators too
    assert int(m.n_estimators) == 200


def test_no_where_radius() -> None:
    """ml/train.py must not contain WHERE radius, 166, neo4j leaks."""
    assert TRAIN_PY.exists(), f"{TRAIN_PY} missing"
    text = TRAIN_PY.read_text(encoding="utf-8")
    # WHERE.*radius
    hits = re.findall(r"WHERE.*radius", text, flags=re.IGNORECASE)
    assert len(hits) == 0, f"WHERE.*radius leak in ml/train.py: {hits}"
    for line in text.splitlines():
        low = line.lower()
        if "where" in low and "radius" in low:
            raise AssertionError(f"radius in WHERE clause: {line}")
    # no 166 aggregation leak
    assert "166" not in text, "166 leak found in ml/train.py"
    assert "neo4j" not in text.lower(), "neo4j forbidden in ml/train.py"
