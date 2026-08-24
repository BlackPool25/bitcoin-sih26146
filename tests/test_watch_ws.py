"""RED tests for M1 S4: watchdog poll, WS /ws/mock/mempool, replay tightened."""

from __future__ import annotations

import contextlib
import csv
import json
import time
from pathlib import Path


def _valid_row(idx: int) -> dict[str, object]:
    return {
        "timestamp": f"2024-01-01T00:0{idx // 60}:{(idx % 60):02d}Z"
        if idx < 60
        else f"2024-01-01T01:00:{(idx % 60):02d}Z",
        "src_ip": "192.168.1.10",
        "dst_ip": "10.0.0.5",
        "src_port": 8333,
        "dst_port": 8334,
        "txid": "a" * 63 + str(idx % 10),
        "input_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "output_addresses": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"],
        "input_amounts": [0.5],
        "output_amounts": [0.4],
        "fee": 0.1,
        "script_type": "P2PKH",
        "geo_country": "US",
        "geo_asn": 15169,
    }


def _row_to_csv_str(row: dict[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in row.items():
        if isinstance(v, list):
            out[k] = json.dumps(v)
        else:
            out[k] = str(v)
    return out


def test_watchdog_poll(tmp_path: Path) -> None:
    """Touch file → via direct handler invocation parquet appears or seen updated."""
    from backend.api.ingest import start_watchdog

    watch_dir = tmp_path / "watch"
    watch_dir.mkdir(parents=True)
    # ensure clean parquet dir
    parquet_dir = Path("data/clean/parquet")
    # call start_watchdog - should not raise
    obs = start_watchdog(poll_dir=str(watch_dir), interval=30)
    try:
        # create a valid csv inside watch_dir
        csv_path = watch_dir / "sample.csv"
        rows = [_valid_row(i) for i in range(3)]
        csv_rows = [_row_to_csv_str(r) for r in rows]
        fieldnames = list(csv_rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(csv_rows)  # type: ignore[arg-type]
        # Give handler debounce 0.5s + processing
        time.sleep(1.2)
        # Simulate filesystem event by directly invoking handler
        # fallback: call ingest via handler manual trigger
        assert obs is not None
        # Check that handler would have processed: parquet should exist
        # For direct handler path, we manually invoke handler if available
        from backend.api.ingest import _handle_watch_file  # type: ignore[attr-defined]

        _handle_watch_file(str(csv_path))
        # Now check parquet count increased
        parquets = list(parquet_dir.glob("*.parquet"))
        assert len(parquets) >= 1
    finally:
        try:
            obs.stop()  # type: ignore[union-attr]
            obs.join(timeout=2)  # type: ignore[union-attr]
        except Exception:
            pass
        # cleanup watch parquets created by watchdog
        for p in Path("data/clean/parquet").glob("*sample*.parquet"):
            with contextlib.suppress(Exception):
                p.unlink()


def test_ws_mempool_shape() -> None:
    """TestClient websocket → recv_json keys blocks+mempool-blocks."""
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    # also verify GET shape
    r = client.get("/api/mock/mempool")
    assert r.status_code == 200
    expected_keys = {"blocks", "mempool-blocks"}
    assert set(r.json().keys()) == expected_keys

    with client.websocket_connect("/ws/mock/mempool") as ws:
        data = ws.receive_json()
        assert "blocks" in data and "mempool-blocks" in data
        assert isinstance(data["blocks"], list) and len(data["blocks"]) >= 1
        assert "height" in data["blocks"][0]
        assert "hash" in data["blocks"][0]


def test_replay_filter(tmp_path: Path) -> None:
    """Replay at mid-timestamp returns subset; missing/invalid → 422; limit 1000."""
    import polars as pl
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    # missing at → 422
    r_missing = client.get("/api/replay")
    assert r_missing.status_code == 422, (
        f"expected 422 for missing at, got {r_missing.status_code}: {r_missing.text}"
    )
    # invalid at → 422
    r_bad = client.get("/api/replay", params={"at": "not-a-date"})
    assert r_bad.status_code == 422

    # timezone variants must parse: Z and +05:30
    for at_val in ["2024-01-01T00:00:30Z", "2024-01-01T05:30:00+05:30"]:
        r = client.get("/api/replay", params={"at": at_val})
        assert r.status_code == 200, f"failed for at={at_val}: {r.text}"

    import backend.api.ingest as ingest_mod

    orig_dir = ingest_mod._PARQUET_DIR  # pyright: ignore[reportPrivateUsage]
    try:
        ingest_mod._PARQUET_DIR = tmp_path  # pyright: ignore[reportPrivateUsage]
        # create parquet with 3 rows at different timestamps
        rows = [_valid_row(i) for i in range(3)]
        # adjust timestamps to be distinct increasing
        rows[0] = {**rows[0], "timestamp": "2024-01-01T00:00:00Z"}
        rows[1] = {**rows[1], "timestamp": "2024-01-01T00:00:30Z"}
        rows[2] = {**rows[2], "timestamp": "2024-01-01T01:00:00Z"}
        df = pl.DataFrame(rows)
        # need to ensure timestamp col is parsed as datetime for filter to work
        # ingest module converts Utf8 via str.to_datetime; so store as string and let filter convert
        parq = tmp_path / "test.parquet"
        df.write_parquet(str(parq))
        # query mid timestamp -> should return 1 or 2 rows (<= at)
        r_mid = client.get("/api/replay", params={"at": "2024-01-01T00:00:15Z"})
        assert r_mid.status_code == 200
        j_mid = r_mid.json()
        assert "rows" in j_mid and "count" in j_mid
        assert j_mid["count"] <= 2
        assert j_mid["count"] >= 1
        # limit 1000 check: create 1005 rows
        many_rows = [_valid_row(i % 10) for i in range(1005)]
        for idx, rr in enumerate(many_rows):
            rr["timestamp"] = f"2024-01-01T00:00:{(idx % 60):02d}Z"
            rr["txid"] = "b" * 63 + str(idx % 10)
        df_many = pl.DataFrame(many_rows)
        parq2 = tmp_path / "many.parquet"
        df_many.write_parquet(str(parq2))
        # remove first parquet to isolate many
        parq.unlink()
        r_many = client.get("/api/replay", params={"at": "2024-01-02T00:00:00Z"})
        assert r_many.status_code == 200
        assert r_many.json()["count"] <= 1000
        assert len(r_many.json()["rows"]) <= 1000
    finally:
        ingest_mod._PARQUET_DIR = orig_dir  # pyright: ignore[reportPrivateUsage]
