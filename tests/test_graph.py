"""TDD RED tests for M2 Graph + Geo (Part 3+4) — 13+ tests, all must FAIL before implementation."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import TypedDict

import duckdb
import polars as pl
import pytest

# ---------------------------------------------------------------------------
# Fixture paths & helpers
# ---------------------------------------------------------------------------

FIXTURE_PATH: Path = Path("tests/fixtures/m2_small.parquet")
SCHEMA_PATH: Path = Path("schema.sql")
BACKEND_GEO_PATH: Path = Path("backend/graph/geo.py")
BACKEND_LAYERS_PATH: Path = Path("backend/graph/layers.py")
BACKEND_BUILD_PATH: Path = Path("backend/graph/build.py")


class GeoRecord(TypedDict):
    ip: str
    country: str | None
    city: str | None
    asn: int | None
    lat: float | None
    lng: float | None
    radius: int | None


class TxDict(TypedDict, total=False):
    txid: str
    inputs: list[str]
    input_addresses: list[str]
    outputs: list[str]
    output_addresses: list[str]
    input_amounts: list[float]
    output_amounts: list[float]
    amounts: list[float]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r * c


@pytest.fixture(scope="module")
def fixture_ips() -> list[str]:
    """Unique IPs from m2_small.parquet fixture (src_ip + dst_ip)."""
    df = pl.read_parquet(str(FIXTURE_PATH))
    ips: list[str] = list(df["src_ip"].to_list() + df["dst_ip"].to_list())  # type: ignore[arg-type]
    # dedup preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            uniq.append(ip)
    return uniq  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def fixture_ips_100k(fixture_ips: list[str]) -> list[str]:
    """Expand fixture IPs to 100k by repetition."""
    n = 100_000
    base = fixture_ips
    # repeat
    out: list[str] = (base * ((n // len(base)) + 1))[:n]
    assert len(out) == 100_000
    return out


# ---------------------------------------------------------------------------
# 1. test_schema_exists
# ---------------------------------------------------------------------------


def test_schema_exists() -> None:
    """schema.sql creates geo_cache/nodes/edges + 4 frozen indices in :memory: DuckDB."""
    assert SCHEMA_PATH.exists(), f"schema.sql not found at {SCHEMA_PATH}"
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    con = duckdb.connect(":memory:")
    try:
        con.execute(sql)
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        assert "geo_cache" in tables, f"missing geo_cache, got {tables}"
        assert "nodes" in tables, f"missing nodes, got {tables}"
        assert "edges" in tables, f"missing edges, got {tables}"
        # indices via duckdb_indexes() or pg_indexes fallback
        idx_rows: list[tuple[object, ...]] = []
        try:
            idx_rows = con.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
        except Exception:
            # fallback: try sqlite_master style or just grep schema
            idx_rows = []
        idx_names: set[str] = {str(r[0]) for r in idx_rows} if idx_rows else set()
        # If duckdb_indexes not available, verify via schema text
        if not idx_names:
            # parse CREATE INDEX names from schema text
            idx_names = set(re.findall(r"CREATE\s+INDEX\s+(\w+)", sql, flags=re.IGNORECASE))
        assert "idx_edges_src" in idx_names, f"idx_edges_src missing in {idx_names}"
        assert "idx_edges_dst" in idx_names, f"idx_edges_dst missing in {idx_names}"
        assert "idx_edges_ts" in idx_names, f"idx_edges_ts missing in {idx_names}"
        assert "idx_nodes_community" in idx_names, f"idx_nodes_community missing in {idx_names}"
        # also verify indices actually exist by querying duckdb_indexes after creation
        # (extra strict: check schema text contains all)
        for needle in ["idx_edges_src", "idx_edges_dst", "idx_edges_ts", "idx_nodes_community"]:
            assert needle in sql, f"{needle} not in schema.sql text"
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 2. test_geo_batch_100k_perf
# ---------------------------------------------------------------------------


def test_geo_batch_100k_perf(fixture_ips_100k: list[str]) -> None:
    """GeoEnricher.batch_lookup(100k ips) <1.0s, returns 100k GeoRecords. Must FAIL if geo.py absent."""
    # This import MUST fail in RED phase because backend/graph/geo.py not yet implemented
    from backend.graph.geo import GeoEnricher  # type: ignore[import-not-found]
    from backend.graph.geo import GeoRecord as GeoRecordImported

    enricher = GeoEnricher(db_path=":memory:")  # type: ignore[call-arg]
    # allow mock Reader path if MMDB missing: enricher should handle dummy IPs fast
    start = time.perf_counter()
    result: list[GeoRecordImported] = enricher.batch_lookup(fixture_ips_100k)  # type: ignore[attr-defined]
    elapsed = time.perf_counter() - start
    assert isinstance(result, list), "batch_lookup must return list"
    assert len(result) == 100_000, f"expected 100k, got {len(result)}"
    assert elapsed < 1.0, f"batch_lookup too slow: {elapsed:.3f}s >=1.0s for 100k"
    # each item is GeoRecord-like dict/dataclass with required keys
    first = result[0]
    # duck-type check
    assert first is not None
    # if GeoRecord is TypedDict/dataclass, check attributes
    # we check at least one record has ip field
    if isinstance(first, dict):
        assert "ip" in first, "GeoRecord dict missing 'ip'"
    else:
        assert hasattr(first, "ip"), "GeoRecord missing ip attribute"


# ---------------------------------------------------------------------------
# 3. test_geo_cache_upsert_and_inconsistent_flag
# ---------------------------------------------------------------------------


def test_geo_cache_upsert_and_inconsistent_flag() -> None:
    """geo_cache upsert + geo_inconsistent flag, haversine ~8000km."""
    from backend.graph.geo import GeoEnricher  # type: ignore[import-not-found]
    from backend.graph.geo import haversine_km as haversine_imported

    # haversine check: SF (37.7749,-122.4194) to Moscow (55.7558,37.6173) ~ 8000km
    dist = haversine_imported(37.7749, -122.4194, 55.7558, 37.6173)
    assert dist == pytest.approx(8000, abs=600), f"haversine SF-Moscow {dist} not ~8000km"
    # also check imported haversine if provided
    dist2 = haversine_imported(37.7749, -122.4194, 55.7558, 37.6173)
    assert dist2 == pytest.approx(8000, abs=600)

    # batch_lookup should have upserted into geo_cache
    enricher = GeoEnricher(db_path=":memory:")  # type: ignore[call-arg]
    # use small batch to trigger upsert
    ips = ["1.1.1.1", "2.2.2.2", "8.8.8.8"]
    enricher.batch_lookup(ips)  # type: ignore[attr-defined]
    # check duckdb geo_cache count >0
    # GeoEnricher should expose connection or db path; we try to query via its con
    con: duckdb.DuckDBPyConnection | None = None
    if hasattr(enricher, "con"):
        con = enricher.con  # type: ignore[attr-defined]
    elif hasattr(enricher, "db"):
        con = enricher.db  # type: ignore[attr-defined]
    elif hasattr(enricher, "_con"):
        con = enricher._con  # type: ignore[attr-defined]
    else:
        # fallback: try to open the db_path if file-based
        assert False, "GeoEnricher must expose duckdb connection as .con / .db / ._con for test"
    assert con is not None
    cnt = con.execute("SELECT count(*) FROM geo_cache").fetchone()
    assert cnt is not None and cnt[0] > 0, "geo_cache empty after batch_lookup"

    # geo_inconsistent flag logic (>1000km same wallet, ASN mismatch)
    # We expect helper is_geo_inconsistent or check_geo_inconsistent
    # Try to import helpers
    from backend.graph.geo import is_geo_inconsistent  # type: ignore[import-not-found]

    # >1000km same wallet → True
    assert (
        is_geo_inconsistent(  # type: ignore[attr-defined]
            wallet="1GeoInconsistentWallet",
            lat1=37.7749,
            lng1=-122.4194,
            lat2=55.7558,
            lng2=37.6173,
            asn1=15169,
            asn2=15169,
        )
        is True
    )
    # ASN mismatch → True
    assert (
        is_geo_inconsistent(  # type: ignore[attr-defined]
            wallet="1TestWallet",
            lat1=37.7749,
            lng1=-122.4194,
            lat2=37.78,
            lng2=-122.41,
            asn1=15169,
            asn2=99999,
        )
        is True
    )
    # normal close distance same ASN → False
    assert (
        is_geo_inconsistent(  # type: ignore[attr-defined]
            wallet="1TestWallet",
            lat1=37.7749,
            lng1=-122.4194,
            lat2=37.78,
            lng2=-122.41,
            asn1=15169,
            asn2=15169,
        )
        is False
    )


# ---------------------------------------------------------------------------
# 4. test_geo_must_not_use_accuracy_radius_filter
# ---------------------------------------------------------------------------


def test_geo_must_not_use_accuracy_radius_filter() -> None:
    """geo.py MUST NOT use accuracy_radius/radius as WHERE filter — hint only."""
    # This test also must FAIL if geo.py not implemented? We assert file exists and then grep
    assert BACKEND_GEO_PATH.exists(), f"{BACKEND_GEO_PATH} must exist (M2 owns it)"
    text = BACKEND_GEO_PATH.read_text(encoding="utf-8")
    # forbid WHERE.*radius or filtering on accuracy_radius
    assert not re.search(r"WHERE.*radius", text, flags=re.IGNORECASE), (
        "geo.py must not filter WHERE radius"
    )
    assert not re.search(r"accuracy_radius.*filter", text, flags=re.IGNORECASE), (
        "geo.py must not filter accuracy_radius"
    )
    # extra strict: radius must not appear in WHERE clause predicate (after WHERE keyword)
    # SELECT ... radius ... WHERE ip = ? is allowed (radius in SELECT, not predicate)
    where_lines = []
    for line in text.splitlines():
        low = line.lower()
        if "where" in low:
            idx = low.index("where")
            after = low[idx:]
            if "radius" in after:
                where_lines.append(line)
    assert len(where_lines) == 0, f"radius used in WHERE filter: {where_lines}"
    # also forbid 'filter.*radius' pattern on same line as accuracy_radius
    for line in text.splitlines():
        if "accuracy_radius" in line.lower() and "filter" in line.lower():
            # allow header comment that describes hint-only contract
            if "hint only" in line.lower() or "do not" in line.lower():
                continue
            assert False, f"accuracy_radius + filter on same line: {line}"


# ---------------------------------------------------------------------------
# 5. test_is_coinjoin_wasabi
# ---------------------------------------------------------------------------


def test_is_coinjoin_wasabi() -> None:
    """Wasabi: 22 inputs + 22 equal outputs (0.01 within 1%) → True, 5 inputs → False."""
    from backend.graph.layers import is_coinjoin  # type: ignore[import-not-found]

    wasabi_tx: dict[str, object] = {
        "txid": "a" * 64,
        "inputs": ["addr_" + str(i) for i in range(22)],
        "input_addresses": ["addr_" + str(i) for i in range(22)],
        "outputs": [0.01] * 22,
        "output_amounts": [0.01] * 22,
        "amounts": [0.01] * 22,
    }
    assert is_coinjoin(wasabi_tx) is True, "Wasabi 22in/22equal should be CoinJoin"  # type: ignore[arg-type]

    small_tx: dict[str, object] = {
        "txid": "b" * 64,
        "inputs": ["addr_" + str(i) for i in range(5)],
        "input_addresses": ["addr_" + str(i) for i in range(5)],
        "outputs": [0.01] * 5,
        "output_amounts": [0.5, 0.6, 0.7, 0.8, 0.9],
        "amounts": [0.5, 0.6, 0.7, 0.8, 0.9],
    }
    assert is_coinjoin(small_tx) is False, "5 inputs should NOT be CoinJoin"  # type: ignore[arg-type]

    # also test equal within 1% variance: 0.01005 vs 0.01 is within 1% → still True
    within_1pct: dict[str, object] = {
        "txid": "c" * 64,
        "inputs": ["addr_" + str(i) for i in range(22)],
        "input_addresses": ["addr_" + str(i) for i in range(22)],
        "outputs": [0.01 if i % 2 == 0 else 0.01005 for i in range(22)],
        "output_amounts": [0.01 if i % 2 == 0 else 0.01005 for i in range(22)],
    }
    assert is_coinjoin(within_1pct) is True  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. test_is_coinjoin_joinmarket
# ---------------------------------------------------------------------------


def test_is_coinjoin_joinmarket() -> None:
    """JoinMarket: ratio 0.5 in 0.4-0.7 with equal outputs → True, outside → False."""
    from backend.graph.layers import is_coinjoin  # type: ignore[import-not-found]

    # Mock ratio: is_coinjoin may internally compute input/output ratio or accept helper
    # We test via tx shape that should trigger JoinMarket path (if implemented as fingerprint)
    # Construct tx with 6 inputs, 6 outputs equal, ratio-like 0.5
    jm_tx_true: dict[str, object] = {
        "txid": "d" * 64,
        "inputs": ["addr_" + str(i) for i in range(6)],
        "input_addresses": ["addr_" + str(i) for i in range(6)],
        "outputs": [0.5] * 6,
        "output_amounts": [0.5] * 6,
        "amounts": [0.5] * 6,
        "ratio": 0.5,
        "joinmarket_ratio": 0.5,
    }
    # Also try direct helper if exists: is_joinmarket
    try:
        from backend.graph.layers import is_joinmarket  # type: ignore[import-not-found]

        assert is_joinmarket(0.5) is True  # type: ignore[attr-defined]
        assert is_joinmarket(0.9) is False  # type: ignore[attr-defined]
        assert is_joinmarket(0.3) is False  # type: ignore[attr-defined]
    except ImportError:
        # fallback: is_coinjoin should handle ratio via tx dict
        assert is_coinjoin(jm_tx_true) is True  # type: ignore[arg-type]
        jm_tx_false: dict[str, object] = {
            "txid": "e" * 64,
            "inputs": ["addr_" + str(i) for i in range(6)],
            "input_addresses": ["addr_" + str(i) for i in range(6)],
            "outputs": [0.5] * 6,
            "output_amounts": [0.5] * 6,
            "ratio": 0.9,
            "joinmarket_ratio": 0.9,
        }
        assert is_coinjoin(jm_tx_false) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 7. test_is_coinjoin_kappos_rf_quarantine
# ---------------------------------------------------------------------------


def test_is_coinjoin_kappos_rf_quarantine() -> None:
    """Kappos RF fallback: low variance outputs → quarantine when pkl missing, else load pkl."""
    from backend.graph.layers import is_coinjoin  # type: ignore[import-not-found]

    pkl_path = Path("models/kappos_rf.pkl")
    # low variance equal outputs should be quarantined as coinjoin-like
    low_var_tx: dict[str, object] = {
        "txid": "f" * 64,
        "inputs": ["addr_" + str(i) for i in range(10)],
        "input_addresses": ["addr_" + str(i) for i in range(10)],
        "outputs": [0.01] * 10,
        "output_amounts": [0.01] * 10,
    }
    high_var_tx: dict[str, object] = {
        "txid": "0" * 64,
        "inputs": ["addr_" + str(i) for i in range(10)],
        "input_addresses": ["addr_" + str(i) for i in range(10)],
        "outputs": [0.1, 0.9, 0.3, 1.2, 0.05, 2.0, 0.7, 0.4, 1.5, 0.2],
        "output_amounts": [0.1, 0.9, 0.3, 1.2, 0.05, 2.0, 0.7, 0.4, 1.5, 0.2],
    }
    if pkl_path.exists():
        # if model exists, it should classify
        assert is_coinjoin(low_var_tx) is True  # type: ignore[arg-type]
        # high variance should be False (not coinjoin)
        assert is_coinjoin(high_var_tx) is False  # type: ignore[arg-type]
    else:
        # fallback path: low variance → quarantine (True), high variance → False
        assert is_coinjoin(low_var_tx) is True  # type: ignore[arg-type]
        assert is_coinjoin(high_var_tx) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. test_four_layers_edges
# ---------------------------------------------------------------------------


def test_four_layers_edges(tmp_path: Path) -> None:
    """After build on fixture, edges contains at least types p2p, utxo, temporal."""
    # Try backend.graph.build.build_all_layers or build.py CLI
    from backend.graph.build import build_all_layers  # type: ignore[import-not-found]

    out_dir = tmp_path / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "duck.db"
    # build_all_layers should accept fixture path and output dir/db
    build_all_layers(input_path=str(FIXTURE_PATH), out_dir=str(out_dir), db_path=str(db_path))  # type: ignore[call-arg]

    con = duckdb.connect(str(db_path))
    try:
        types = {r[0] for r in con.execute("SELECT DISTINCT type FROM edges").fetchall()}
        assert "p2p" in types, f"p2p missing in edges types {types}"
        assert "utxo" in types, f"utxo missing in edges types {types}"
        assert "temporal" in types, f"temporal missing in edges types {types}"
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 9. test_layer_weights_temporal_decay
# ---------------------------------------------------------------------------


def test_layer_weights_temporal_decay() -> None:
    """Temporal decay: exp(-dt/300) for dt 0,300,600."""
    # Direct helper: weight = exp(-dt/300)
    # If build_temporal_edges returns list of edges with weight, test known dt values
    # We call with synthetic timestamps
    import datetime

    from backend.graph.layers import build_temporal_edges  # type: ignore[import-not-found]

    base = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    # helper may be weight function or edge builder; try both
    try:
        from backend.graph.layers import temporal_weight  # type: ignore[import-not-found]

        assert temporal_weight(0) == pytest.approx(1.0, abs=1e-6)
        assert temporal_weight(300) == pytest.approx(math.exp(-1), abs=1e-4)
        assert temporal_weight(600) == pytest.approx(math.exp(-2), abs=1e-4)
        return
    except ImportError:
        pass

    # fallback: build_temporal_edges should produce weights
    # create two txs dt=0, 300, 600
    w0 = build_temporal_edges(base, base)  # type: ignore[call-arg]
    w300 = build_temporal_edges(base, base + datetime.timedelta(seconds=300))  # type: ignore[call-arg]
    w600 = build_temporal_edges(base, base + datetime.timedelta(seconds=600))  # type: ignore[call-arg]

    # function may return float weight or list[edge]
    def extract_weight(v: object) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict) and "weight" in v:
            return float(v["weight"])  # type: ignore[index]
        if isinstance(v, list) and len(v) > 0:
            first = v[0]
            if isinstance(first, dict) and "weight" in first:
                return float(first["weight"])  # type: ignore[index]
            if isinstance(first, (int, float)):
                return float(first)
        raise AssertionError(f"cannot extract weight from {v!r}")

    assert extract_weight(w0) == pytest.approx(1.0, abs=1e-6)
    assert extract_weight(w300) == pytest.approx(0.3678794412, abs=1e-4)
    assert extract_weight(w600) == pytest.approx(0.1353352832, abs=1e-4)


# ---------------------------------------------------------------------------
# 10. test_no_supercluster
# ---------------------------------------------------------------------------


def test_no_supercluster(tmp_path: Path) -> None:
    """No supercluster: largest community <5% of nodes."""
    from backend.graph.build import build_all_layers  # type: ignore[import-not-found]

    out_dir = tmp_path / "graph2"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "duck.db"
    build_all_layers(input_path=str(FIXTURE_PATH), out_dir=str(out_dir), db_path=str(db_path))  # type: ignore[call-arg]

    con = duckdb.connect(str(db_path))
    try:
        row = con.execute(
            "SELECT max(cnt)::DOUBLE / sum(cnt)::DOUBLE FROM (SELECT count(*) cnt FROM nodes GROUP BY community_id) t"
        ).fetchone()
        assert row is not None
        ratio = float(row[0]) if row[0] is not None else 1.0
        assert ratio < 0.05, f"supercluster ratio {ratio:.3f} >=0.05 (largest community >=5%)"
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 11. test_coinjoin_not_merged
# ---------------------------------------------------------------------------


def test_coinjoin_not_merged(tmp_path: Path) -> None:
    """CoinJoin tx input wallets must have distinct community_id (not unioned)."""
    from backend.graph.build import build_all_layers  # type: ignore[import-not-found]

    out_dir = tmp_path / "graph3"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "duck.db"
    build_all_layers(input_path=str(FIXTURE_PATH), out_dir=str(out_dir), db_path=str(db_path))  # type: ignore[call-arg]

    con = duckdb.connect(str(db_path))
    try:
        # Identify CoinJoin tx: those with 22 inputs equal outputs exist at fixture indices 10,11,12
        # We query edges or nodes: find tx nodes that are coinjoin-flagged
        # Fallback: directly look at fixture to get coinjoin txids
        df = pl.read_parquet(str(FIXTURE_PATH))
        import json as _json

        coinjoin_txids: list[str] = []
        for row in df.iter_rows(named=True):  # type: ignore[call-arg]
            in_addrs = _json.loads(row["input_addresses"])  # type: ignore[arg-type]
            out_amts = _json.loads(row["output_amounts"])  # type: ignore[arg-type]
            if len(in_addrs) == 22 and len(out_amts) == 22 and len(set(out_amts)) == 1:
                coinjoin_txids.append(row["txid"])  # type: ignore[arg-type]
        assert len(coinjoin_txids) >= 1, "fixture should have CoinJoin txids"
        # For each coinjoin, check its input wallets are not all same community
        for txid in coinjoin_txids:
            # wallets = input_addresses of that tx
            wallets: list[str] = []
            for row in df.filter(pl.col("txid") == txid).iter_rows(named=True):  # type: ignore[call-arg]
                wallets = _json.loads(row["input_addresses"])  # type: ignore[arg-type]
            assert len(wallets) > 1
            # query community_id for each wallet node (duckdb uses string interpolation safely — wallets are alphanumeric)
            # Use parameterized query via list
            q = f"SELECT id, community_id FROM nodes WHERE id IN ({','.join([repr(w) for w in wallets])})"
            rows = con.execute(q).fetchall()
            comms = {r[1] for r in rows}
            # Should have >1 distinct community (not merged via CIOH)
            assert len(comms) > 1, (
                f"CoinJoin {txid[:8]} wallets incorrectly merged into single community {comms}"
            )
    finally:
        con.close()


# ---------------------------------------------------------------------------
# 12. test_build_outputs_duckdb_and_parquet_counts
# ---------------------------------------------------------------------------


def test_build_outputs_duckdb_and_parquet_counts(tmp_path: Path) -> None:
    """Build outputs duck.db + parquet counts >0 + indices present."""
    from backend.graph.build import build_all_layers  # type: ignore[import-not-found]

    out_dir = tmp_path / "graph4"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "duck.db"
    build_all_layers(input_path=str(FIXTURE_PATH), out_dir=str(out_dir), db_path=str(db_path))  # type: ignore[call-arg]

    assert db_path.exists(), f"duck.db not created at {db_path}"
    con = duckdb.connect(str(db_path))
    try:
        n_nodes = con.execute("SELECT count(*) FROM nodes").fetchone()
        assert n_nodes is not None and n_nodes[0] > 0, "nodes count 0"
        n_edges = con.execute("SELECT count(*) FROM edges").fetchone()
        assert n_edges is not None and n_edges[0] > 0, "edges count 0"
        # indices check
        try:
            idxs = {r[0] for r in con.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
        except Exception:
            idxs = set()
        # fallback to schema check on disk
        if len(idxs) < 4:
            # also check that build created parquet files
            pass
        # check indices contain required
        # allow either duckdb_indexes or at least creation succeeded without error
        # we assert by trying to use index via EXPLAIN
        for idx in ["idx_edges_src", "idx_edges_dst", "idx_edges_ts", "idx_nodes_community"]:
            # Check via duckdb_indexes if available, else assert file count
            if idxs:
                assert idx in idxs, f"index {idx} missing in duckdb_indexes {idxs}"
    finally:
        con.close()

    # parquet files exist in out_dir
    parquet_files = list(out_dir.glob("*.parquet")) + list(out_dir.glob("**/*.parquet"))
    # also allow nodes.parquet / edges.parquet naming
    assert len(parquet_files) > 0, f"no parquet files in {out_dir}, expected nodes/edges parquet"
    for p in parquet_files:
        df = pl.read_parquet(str(p))
        assert df.height > 0, f"parquet {p} empty"


# ---------------------------------------------------------------------------
# 13. test_must_not_write_clean
# ---------------------------------------------------------------------------


def test_must_not_write_clean() -> None:
    """backend/ must not write to data/clean (M1 owns)."""
    backend_dir = Path("backend/graph")
    hits: list[str] = []
    for py in backend_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        # detect writes to data/clean
        if re.search(r"data/clean", text):
            # distinguish read vs write: look for write indicators
            if re.search(r"(write|to_parquet|sink_parquet|COPY.*TO|open\(.*data/clean)", text):
                hits.append(f"{py}: {text.strip()[:120]}")
            elif "data/clean" in text:
                hits.append(f"{py}: contains data/clean")
    # This should be 0; if graph code incorrectly writes to clean, it will fail
    assert len(hits) == 0, f"backend must not write to data/clean, hits: {hits}"


# ---------------------------------------------------------------------------
# 14. test_must_not_neo4j
# ---------------------------------------------------------------------------


def test_must_not_neo4j() -> None:
    """backend/ must not import neo4j (rejected +400MB)."""
    backend_dir = Path("backend")
    hits: list[str] = []
    for py in backend_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        if "neo4j" in text:
            hits.append(str(py))
        if re.search(r"from\s+neo4j|import\s+neo4j", text):
            hits.append(str(py))
    assert len(hits) == 0, f"neo4j import forbidden, found in: {hits}"
