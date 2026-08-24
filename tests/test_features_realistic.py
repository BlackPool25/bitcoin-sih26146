"""TDD realistic features: 10K via generate_synthetic --scale 10k --seed 42 => n_unique>5 for 30/38."""

from __future__ import annotations

import json
import re
import subprocess
import sys
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
ML_FEATURES_PY = Path("ml/features.py")


def test_realistic_n_unique() -> None:
    """At least 30/38 features have n_unique>5 (degenerate <=8)."""
    assert FEATURES_PARQUET.exists(), f"{FEATURES_PARQUET} missing — run ml/features.py"
    df = pl.read_parquet(str(FEATURES_PARQUET))
    assert df.columns == FEATURE_NAMES
    assert df.width == 38
    deg = [c for c in FEATURE_NAMES if df[c].n_unique() <= 5]
    ok = sum(1 for c in FEATURE_NAMES if df[c].n_unique() > 5)
    assert ok >= 30, f"only {ok}/38 have n_unique>5, degenerate {deg}"
    assert len(deg) <= 8, f"degenerate {len(deg)} >8: {deg}"


def test_realistic_via_10k() -> None:
    """Generate 10K via script and rebuild features -> still 30/38."""
    # ensure synth 10k exists; generate if missing
    synth_csv = Path("data/raw/synthetic/synth_10k.csv")
    if not synth_csv.exists():
        subprocess.run(
            [sys.executable, "scripts/generate_synthetic.py", "--scale", "10k", "--seed", "42", "--format", "csv"],
            check=True,
        )
    assert synth_csv.exists()
    # build parquet for feature input
    import tempfile

    tmp_parq = Path(tempfile.gettempdir()) / "synth_10k_test.parquet"
    tmp_out = Path(tempfile.gettempdir()) / "feat10k_test"
    # convert csv to parquet if needed
    if not tmp_parq.exists():
        df_raw = pl.read_csv(str(synth_csv), infer_schema_length=10000)
        df_raw.write_parquet(str(tmp_parq))
    # build features
    subprocess.run(
        [sys.executable, "-m", "ml.features", "--graph", str(tmp_parq), "--out", str(tmp_out)],
        check=True,
    )
    feat = tmp_out / "features.parquet"
    assert feat.exists()
    df = pl.read_parquet(str(feat))
    ok = sum(1 for c in df.columns if df[c].n_unique() > 5)
    assert ok >= 30, f"10k realistic only {ok}/38 >5"
    names = json.loads((tmp_out / "feature_names.json").read_text(encoding="utf-8"))
    assert names == FEATURE_NAMES


def test_no_where_radius() -> None:
    assert ML_FEATURES_PY.exists()
    text = ML_FEATURES_PY.read_text(encoding="utf-8")
    hits = re.findall(r"WHERE.*radius", text, flags=re.IGNORECASE)
    assert len(hits) == 0, f"WHERE.*radius leak: {hits}"


def test_no_166_leak() -> None:
    assert ML_FEATURES_PY.exists()
    text = ML_FEATURES_PY.read_text(encoding="utf-8")
    assert "166" not in text, "166 leak found"
    assert "neo4j" not in text.lower(), "neo4j forbidden"
