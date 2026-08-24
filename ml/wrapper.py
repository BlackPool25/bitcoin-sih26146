"""ml/wrapper.py — IFProbWrapper for calibrate prefit."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin  # type: ignore[import-untyped]


class IFProbWrapper(BaseEstimator, ClassifierMixin):  # type: ignore[misc]
    """Dummy classifier wrapping p_raw for CalibratedClassifierCV prefit."""

    def __init__(self) -> None:
        self.classes_: np.ndarray[Any, Any] = np.array([0, 1])

    def fit(self, X: np.ndarray[Any, Any], y: np.ndarray[Any, Any] | None = None) -> IFProbWrapper:  # type: ignore[override]
        _ = X
        _ = y
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:  # type: ignore[override]
        if X.ndim == 2:
            p = np.asarray(X[:, 0], dtype=np.float64)
        else:
            p = np.asarray(X, dtype=np.float64)
        p = np.clip(p, 1e-7, 1 - 1e-7)
        return np.column_stack([1 - p, p])

    def predict(self, X: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:  # type: ignore[override]
        proba = self.predict_proba(X)
        return (proba[:, 1] > 0.5).astype(int)

    def decision_function(self, X: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        if X.ndim == 2:
            return np.asarray(X[:, 0], dtype=np.float64)
        return np.asarray(X, dtype=np.float64)
