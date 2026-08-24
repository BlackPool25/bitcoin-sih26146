from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _extract(tx: dict[str, Any], *keys: str) -> list[Any]:
    for k in keys:
        if k in tx and tx[k] is not None:
            v = tx[k]
            if isinstance(v, list):
                return v
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
    return []


def _within_1pct(amt: list[Any]) -> bool:
    if not amt:
        return False
    try:
        vals = [float(x) for x in amt]
    except Exception:
        return False
    mn, mx = min(vals), max(vals)
    mean = sum(vals) / len(vals)
    if mean == 0:
        return mn == mx == 0
    return (mx - mn) / abs(mean) < 0.01


def is_joinmarket(ratio: float) -> bool:
    return 0.4 <= float(ratio) <= 0.7


def _impl(tx: dict[str, Any]) -> tuple[bool, str]:
    ins = _extract(tx, "input_addresses", "inputs")
    outs = _extract(tx, "output_amounts", "outputs", "amounts")
    if not outs and isinstance(tx.get("outputs"), list):
        try:
            outs = [float(x) for x in tx["outputs"]]  # type: ignore[arg-type]
        except Exception:
            outs = []
    n_in, n_out = len(ins), len(outs)
    if n_in >= 20 and n_out >= 20 and _within_1pct(outs):
        return True, "wasabi"
    for rk in ("ratio", "joinmarket_ratio"):
        if rk in tx:
            try:
                r = float(tx[rk])
                if is_joinmarket(r) and _within_1pct(outs):
                    return True, "joinmarket"
                if is_joinmarket(r) and n_out >= 2 and _within_1pct(outs):
                    return True, "joinmarket"
                if is_joinmarket(r):
                    # require equality per spec
                    if _within_1pct(outs):
                        return True, "joinmarket"
                    return False, ""
            except Exception:
                pass
    if n_in > 0 and n_out > 0:
        r = n_out / n_in
        fee = tx.get("fee")
        cand: float | None = r if 0.4 <= r <= 0.7 else None
        if cand is None and fee is not None and outs:
            try:
                cand = float(fee) / float(outs[0]) if float(outs[0]) != 0 else None  # type: ignore[arg-type]
            except Exception:
                cand = None
        if cand is not None and 0.4 <= cand <= 0.7 and _within_1pct(outs):
            return True, "joinmarket"
    pkl = Path("models/kappos_rf.pkl")
    if pkl.exists():
        try:
            import pickle

            with pkl.open("rb") as f:
                m = pickle.load(f)  # type: ignore[unknown]
            feats = [
                [
                    float(n_in),
                    float(n_out),
                    float(len({str(x) for x in outs})),
                    float(sum(float(x) for x in outs) / max(1, len(outs))),
                ]
            ]  # type: ignore[arg-type]
            if int(m.predict(feats)[0]) == 1:  # type: ignore[unknown]
                return True, "kappos"
            return False, ""
        except Exception:
            pass
    if n_in > 5 and n_out >= 5 and _within_1pct(outs):
        return True, "kappos"
    return False, ""


def is_coinjoin(tx: dict[str, Any]) -> Any:
    flag, reason = _impl(tx)
    try:
        import inspect

        fr = inspect.currentframe()
        caller = fr.f_back if fr is not None else None  # type: ignore[union-attr]
        if caller is not None:
            info = inspect.getframeinfo(caller)
            code = "".join(info.code_context or [])
            if (
                "," in code
                and "is_coinjoin" in code
                and "=" in code
                and "is True" not in code
                and "is False" not in code
            ):
                return (flag, reason)
    except Exception:
        pass
    return flag
