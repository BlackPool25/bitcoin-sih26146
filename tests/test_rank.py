"""TDD RED tests for T06 ml/calibrate.py — Platt prefit + Isotonic challenger ECE<0.05 tiers."""

from __future__ import annotations

import pickle
import re
from pathlib import Path

CALIBRATE_PY = Path("ml/calibrate.py")
CALIBRATOR_PKL = Path("models/calibrator.pkl")
CALIBRATION_JSON = Path("data/eval/calibration.json")
RANKED_CANDIDATES = [
    Path("data/alerts/ranked.parquet"),
    Path("data/eval/ranked.parquet"),
    Path("data/ranked.parquet"),
]


def _find_ranked() -> Path | None:
    for p in RANKED_CANDIDATES:
        if p.exists():
            return p
    # glob fallback
    for p in Path("data").rglob("ranked.parquet"):
        return p
    return None


def test_tiers_monotonic() -> None:
    """ranked.parquet sorted p_calibrated desc and tier boundaries monotonic."""
    ranked = _find_ranked()
    assert ranked is not None, (
        f"ranked.parquet not found in {RANKED_CANDIDATES} — run ml/calibrate.py"
    )
    import polars as pl

    df = pl.read_parquet(str(ranked))
    # locate p_calibrated column (allow p_calibrated / p / prob)
    p_col = None
    for cand in ("p_calibrated", "p_cal", "prob", "p_raw"):
        if cand in df.columns:
            p_col = cand
            break
    assert p_col is not None, f"p_calibrated column missing; columns={df.columns}"
    tier_col = None
    for cand in ("tier", "risk_tier", "level"):
        if cand in df.columns:
            tier_col = cand
            break
    assert tier_col is not None, f"tier column missing; columns={df.columns}"
    probs = df[p_col].to_list()
    # check sorted desc
    assert probs == sorted(probs, reverse=True), "ranked.parquet not sorted p_calibrated desc"
    # tier monotonic: Critical > High > Medium > Low in severity
    order = {
        "Critical": 4, "High": 3, "Medium": 2, "Low": 1,
        "critical": 4, "high": 3, "medium": 2, "low": 1,
    }
    tiers = df[tier_col].to_list()
    # map to severity rank
    ranks = [order.get(str(t), -1) for t in tiers]
    assert all(r != -1 for r in ranks), f"unknown tier values: {set(tiers)}"
    # monotonic non-increasing with descending prob (since high prob = high severity)
    for i in range(1, len(ranks)):
        assert ranks[i] <= ranks[i - 1], (
            f"tier monotonic violation at {i}: "
            f"{tiers[i-1]}({ranks[i-1]}) -> {tiers[i]}({ranks[i]}) "
            f"p {probs[i-1]:.4f} -> {probs[i]:.4f}"
        )
    # also verify boundary semantics: each tier's probs must respect thresholds
    # Critical >0.90, High 0.75-0.90, Medium 0.50-0.75, Low <=0.50
    for p, t in zip(probs, tiers, strict=False):
        ts = str(t)
        if ts.lower() == "critical":
            assert float(p) > 0.90, f"Critical tier p={p} not >0.90"
        elif ts.lower() == "high":
            assert 0.75 < float(p) <= 0.90, f"High tier p={p} not in (0.75,0.90]"
        elif ts.lower() == "medium":
            assert 0.50 < float(p) <= 0.75, f"Medium tier p={p} not in (0.50,0.75]"
        else:
            assert float(p) <= 0.50, f"Low tier p={p} not <=0.50"


def test_ece_lt_05() -> None:
    """calibrator.pkl ece <0.05 and calibration.json ece <0.05."""
    assert CALIBRATOR_PKL.exists(), f"{CALIBRATOR_PKL} not found — run ml/calibrate.py"
    data = pickle.loads(CALIBRATOR_PKL.read_bytes())
    assert isinstance(data, dict), "calibrator.pkl must be dict"
    # accept ece or platt_ece
    ece = data.get("ece", data.get("platt_ece", None))
    assert ece is not None, f"ece missing in calibrator.pkl keys={list(data.keys())}"
    ece_f = float(ece)  # type: ignore[arg-type]
    assert ece_f < 0.05, f"ece {ece_f:.4f} >=0.05"
    if CALIBRATION_JSON.exists():
        import json

        j = json.loads(CALIBRATION_JSON.read_text(encoding="utf-8"))
        je = j.get("ece", j.get("platt_ece", None))
        assert je is not None, "ece missing in calibration.json"
        assert float(je) < 0.05, f"calibration.json ece {float(je):.4f} >=0.05"


def test_calibrator_prefit_sigmoid() -> None:
    """grep CalibratedClassifierCV.*prefit.*sigmoid in ml/calibrate.py."""
    assert CALIBRATE_PY.exists(), f"{CALIBRATE_PY} missing — implement ml/calibrate.py"
    text = CALIBRATE_PY.read_text(encoding="utf-8")
    # must contain CalibratedClassifierCV, cv=\"prefit\", method=\"sigmoid\" on same logical line
    assert "CalibratedClassifierCV" in text, "CalibratedClassifierCV not found in ml/calibrate.py"
    # check combined pattern
    pattern = re.compile(
        r"CalibratedClassifierCV.*prefit.*sigmoid", re.DOTALL | re.IGNORECASE
    )
    assert pattern.search(text) is not None, (
        'CalibratedClassifierCV.*prefit.*sigmoid not found '
        '(need cv="prefit" method="sigmoid" with CalibratedClassifierCV)'
    )
    # also ensure literal strings exist separately
    assert (
        'cv="prefit"' in text or "cv='prefit'" in text or 'cv = "prefit"' in text
    ), 'cv="prefit" literal not found'
    assert (
        'method="sigmoid"' in text
        or "method='sigmoid'" in text
        or 'method = "sigmoid"' in text
    ), 'method="sigmoid" literal not found'


def test_isotonic_clip() -> None:
    """grep IsotonicRegression.*clip in ml/calibrate.py."""
    assert CALIBRATE_PY.exists(), f"{CALIBRATE_PY} missing"
    text = CALIBRATE_PY.read_text(encoding="utf-8")
    assert "IsotonicRegression" in text, "IsotonicRegression not found in ml/calibrate.py"
    pattern = re.compile(r"IsotonicRegression.*clip", re.DOTALL | re.IGNORECASE)
    assert pattern.search(text) is not None, (
        'IsotonicRegression.*clip not found (need out_of_bounds="clip")'
    )
    assert (
        'out_of_bounds="clip"' in text or "out_of_bounds='clip'" in text
    ), 'out_of_bounds="clip" literal not found'


def test_tier_thresholds() -> None:
    """grep 0.90.*0.75.*0.50 in ml/calibrate.py."""
    assert CALIBRATE_PY.exists(), f"{CALIBRATE_PY} missing"
    text = CALIBRATE_PY.read_text(encoding="utf-8")
    pattern = re.compile(r"0\.90.*0\.75.*0\.50", re.DOTALL)
    assert pattern.search(text) is not None, (
        "0.90.*0.75.*0.50 not found in ml/calibrate.py — "
        "tier thresholds 0.90/0.75/0.50 must appear in order"
    )
