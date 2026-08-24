"""M3 guardrails: no WHERE radius, no 166 leak, no GNN train at finale."""

from __future__ import annotations

import re
from pathlib import Path


def test_no_where_radius() -> None:
    """grep -ri WHERE.*radius ml/ backend/graph/ ==0 except comment hint only."""
    roots = [Path("ml"), Path("backend/graph")]
    hits: list[str] = []
    pat = re.compile(r"WHERE.*radius", re.IGNORECASE)
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            text = p.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    stripped = line.strip()
                    # allow comment hint lines only
                    low = stripped.lower()
                    is_comment_hint = stripped.startswith("#") and (
                        "hint" in low or "do not use" in low or "informational" in low
                    )
                    if is_comment_hint:
                        continue
                    hits.append(f"{p}:{i}:{line.strip()}")
    assert len(hits) == 0, f"WHERE.*radius leak: {hits}"


def test_no_166_leak() -> None:
    """ml/explain.py must not contain 166 leaked agg except comment hint."""
    p = Path("ml/explain.py")
    assert p.exists(), "ml/explain.py missing"
    text = p.read_text(encoding="utf-8")
    if "166" not in text:
        return
    # allow only comment containing do NOT SHAP leaked 166
    allowed_comment = "do NOT SHAP leaked 166"
    for i, line in enumerate(text.splitlines(), start=1):
        if "166" in line:
            stripped = line.strip()
            if stripped.startswith("#") and allowed_comment in stripped:
                continue
            raise AssertionError(f"166 leak at ml/explain.py:{i}: {line.strip()}")


def test_no_gnn_train_at_finale() -> None:
    """ml/infer.py must not invoke train_gnn --epochs or call optimizer at import."""
    p = Path("ml/infer.py")
    assert p.exists(), "ml/infer.py missing"
    text = p.read_text(encoding="utf-8")
    hits = re.findall(r"train_gnn.*--epochs", text)
    assert len(hits) == 0, f"train_gnn --epochs leak in ml/infer.py: {hits}"
    # also forbid optimizer instantiation at import/top-level in infer.py
    # allow optimizer inside train_gnn.py only; infer.py should not contain optimizer
    # check for optimizer( or torch.optim patterns unless guarded
    opt_hits = re.findall(r"optimizer", text, flags=re.IGNORECASE)
    assert len(opt_hits) == 0, f"optimizer leak in ml/infer.py: {opt_hits}"
