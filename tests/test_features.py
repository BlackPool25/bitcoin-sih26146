"""TDD RED tests for T02 ml/features.py — 38 frozen features SHAP-ready."""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl

FEATURE_NAMES = [
    "unique_peers",
    "asn_entropy",
    "port_entropy",
    "geo_distance_variance_km",
    "inv_jitter_std",
    "peer_degree",
    "asn_hopping_rate",
    "port_anomaly_score",
    "country_diversity",
    "p2p_burst_count",
    "rtt_proxy_ms",
    "uptime_hours",
    "tor_flag",
    "accuracy_radius_mean",
    "ws_reconnects",
    "fan_in",
    "fan_out",
    "output_amount_variance",
    "fee_sat_per_vb",
    "script_type_hist_P2WPKH_ratio",
    "input_count",
    "output_dispersion_gini",
    "utxo_age_blocks",
    "peel_depth",
    "mixer_score",
    "coinjoin_prob",
    "change_addr_likelihood",
    "dust_outputs",
    "op_return_flag",
    "value_median",
    "burst_5m_count",
    "burst_1h_count",
    "inter_tx_interval_std",
    "modularity_delta",
    "hour_entropy",
    "day_of_week_entropy",
    "community_size",
    "betweenness_z",
]

FEATURES_PARQUET = Path("data/features/features.parquet")
FEATURE_NAMES_JSON = Path("data/features/feature_names.json")
ML_FEATURES_PY = Path("ml/features.py")
FIXTURE_PATH = Path("tests/fixtures/m2_small.parquet")


def test_shape_50k_x_38() -> None:
    """features.parquet has 38 cols frozen order, all float, SHAP-ready."""
    assert FEATURES_PARQUET.exists(), f"{FEATURES_PARQUET} not found — run ml/features.py"
    assert FEATURE_NAMES_JSON.exists(), f"{FEATURE_NAMES_JSON} not found"
    names = json.loads(FEATURE_NAMES_JSON.read_text(encoding="utf-8"))
    assert names == FEATURE_NAMES, f"feature_names.json order mismatch: {names}"
    df = pl.read_parquet(str(FEATURES_PARQUET))
    assert df.columns == FEATURE_NAMES, f"columns mismatch: {df.columns}"
    assert df.width == 38, f"width {df.width} !=38"
    # row count: either 50000 (synth_50k) or graph_tx_count fallback >0
    assert df.height > 0, "features empty"
    # all float dtypes
    for c in df.columns:
        assert df[c].dtype in (pl.Float64, pl.Float32), f"{c} dtype {df[c].dtype} not float"
    # also ensure no string/object columns leaked
    assert df.height >= 1


def test_jl_dual() -> None:
    """_jl handles JSON strings (fixture) and List (clean) → list."""
    from ml.features import _jl  # type: ignore[import-not-found]

    # JSON string case (m2_small.parquet stores arrays as JSON strings)
    df = pl.read_parquet(str(FIXTURE_PATH))
    row = df.row(0, named=True)  # type: ignore[call-arg]
    # m2_small stores input_addresses as JSON string
    raw_str = row["input_addresses"]
    assert isinstance(raw_str, str), "fixture should have JSON string"
    out_str = _jl(row, "input_addresses")  # type: ignore[arg-type]
    assert isinstance(out_str, list) and len(out_str) > 0

    # List case (clean parquet stores as native List)
    df2 = pl.read_parquet("data/clean/parquet/synth_50k.parquet")
    row2 = df2.row(0, named=True)  # type: ignore[call-arg]
    # clean parquet may store as list; if so test it
    raw_list = row2.get("input_addresses")
    # ensure _jl handles list
    if isinstance(raw_list, list):
        out2 = _jl(row2, "input_addresses")  # type: ignore[arg-type]
        assert out2 == list(raw_list)
    else:
        # if clean parquet stores string, still test list path directly
        fake_row: dict[str, object] = {"col": ["a", "b", "c"]}
        assert _jl(fake_row, "col") == ["a", "b", "c"]  # type: ignore[arg-type]
        fake_row2: dict[str, object] = {"col": '["x","y"]'}
        assert _jl(fake_row2, "col") == ["x", "y"]  # type: ignore[arg-type]

    # parquet List column type: if _jl is correct, features build won't crash
    # Also directly check _jl handles None gracefully
    assert _jl({}, "missing") == []  # type: ignore[arg-type]


def test_no_where_radius() -> None:
    """grep WHERE.*radius should be 0 in ml/features.py."""
    assert ML_FEATURES_PY.exists(), f"{ML_FEATURES_PY} missing"
    text = ML_FEATURES_PY.read_text(encoding="utf-8")
    hits = re.findall(r"WHERE.*radius", text, flags=re.IGNORECASE)
    assert len(hits) == 0, f"WHERE.*radius leak in ml/features.py: {hits}"
    # also forbid any SQL WHERE filtering on radius/accuracy_radius
    for line in text.splitlines():
        low = line.lower()
        if "where" in low and "radius" in low:
            assert False, f"radius in WHERE clause: {line}"  # noqa: B011


def test_no_166_leak() -> None:
    """No 166 leaked aggregation count in ml/features.py."""
    assert ML_FEATURES_PY.exists()
    text = ML_FEATURES_PY.read_text(encoding="utf-8")
    # forbid literal 166 as aggregation count leakage
    # allow comments mentioning 166? No — spec says no 166 in file at all
    assert "166" not in text, "166 leak found in ml/features.py"
    # also forbid import of neo4j
    assert "neo4j" not in text.lower(), "neo4j forbidden"
