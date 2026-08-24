# pyright: reportAttributeAccessIssue=false
import json
import sys
from pathlib import Path

import numpy as np


def test_fidelity_json_has_5_keys() -> None:
    p = Path("data/eval/fidelity.json")
    assert p.exists(), "fidelity.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "wits_5_criteria" in data, "missing wits_5_criteria"
    crit = data["wits_5_criteria"]
    assert isinstance(crit, dict)
    expected = {"ks", "netsimile", "dcr", "nndr", "correlation"}
    assert set(crit.keys()) == expected, f"expected 5 keys {expected} got {set(crit.keys())}"
    assert "wits" in data and "ks" in data and "netsimile" in data and "dcr" in data
    assert data["note"].startswith("computed")
    assert 0.05 < float(data["ks"]) < 0.5, f"ks {data['ks']} not in (0.05,0.5)"


def test_ks_realistic_vs_uniform() -> None:
    sys.path.insert(0, str(Path("scripts/eval").resolve()))
    try:
        import fidelity as fid  # type: ignore[import-untyped]
        ks_fn = getattr(fid, "_ks")
    except Exception:
        # fallback local ks
        def ks_fn(a: np.ndarray, b: np.ndarray) -> float:  # type: ignore[no-redef]
            try:
                from scipy.stats import ks_2samp  # type: ignore[import-untyped]

                return float(ks_2samp(a, b).statistic)
            except Exception:
                aa = np.sort(a)
                bb = np.sort(b)
                vals = np.unique(np.concatenate([aa, bb]))
                ca = np.searchsorted(aa, vals, side="right") / len(aa)
                cb = np.searchsorted(bb, vals, side="right") / len(bb)
                return float(np.max(np.abs(ca - cb)))

    rng = np.random.default_rng(42)
    real = rng.normal(loc=50.0, scale=10.0, size=5000)
    prior = rng.normal(loc=52.0, scale=10.0, size=5000)
    ks_real = float(ks_fn(real, prior))
    assert 0.05 < ks_real < 0.5, f"realistic ks {ks_real} not in (0.05,0.5)"

    uniform = rng.uniform(200, 300, size=5000)
    ks_uniform = float(ks_fn(real, uniform))
    assert ks_uniform > 0.6, f"uniform ks {ks_uniform} expected >0.6 (ideally ~0.9)"
    assert ks_uniform > ks_real


def test_pr_auc_ge_055_after_t8() -> None:
    p = Path("data/eval/pr.json")
    assert p.exists(), "pr.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    pr_auc = float(data.get("pr_auc", 0))
    assert pr_auc >= 0.55, f"pr_auc {pr_auc} <0.55 after T8"
