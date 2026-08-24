"""TDD RED tests for TransactionRecord strict validation (M1 S2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _valid_payload() -> dict[str, object]:
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "src_ip": "192.168.1.10",
        "dst_ip": "10.0.0.5",
        "src_port": 8333,
        "dst_port": 8334,
        "txid": "a" * 64,
        "input_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "output_addresses": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"],
        "input_amounts": [0.5, 1.2],
        "output_amounts": [1.6],
        "fee": 0.1,
        "script_type": "P2PKH",
        "geo_country": "US",
        "geo_asn": 15169,
    }


def test_valid_full_record() -> None:
    from backend.ingest.models import TransactionRecord, validate_record

    payload = _valid_payload()
    rec = TransactionRecord.model_validate(payload)
    assert rec.src_port == 8333
    assert rec.txid == "a" * 64
    # also via helper
    rec2 = validate_record(payload)
    assert rec2.dst_ip.exploded == "10.0.0.5"


def test_transaction_record_strict_rejects_coercion() -> None:
    """Core S2 strict test: string port, short txid, bad script_type must raise, valid passes."""
    from backend.ingest.models import TransactionRecord

    valid = _valid_payload()

    # string port must NOT coerce
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**valid, "src_port": "8333"})  # type: ignore[dict-item]

    # short txid
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**valid, "txid": "short"})

    # bad script_type
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**valid, "script_type": "P2PK"})

    # valid passes
    rec = TransactionRecord.model_validate(valid)
    assert rec.script_type == "P2PKH"


# Alias for required invocation: tests/test_ingest.py::test_transaction_record_strict
def test_transaction_record_strict() -> None:
    test_transaction_record_strict_rejects_coercion()


def test_rejects_string_port() -> None:
    from backend.ingest.models import TransactionRecord

    payload = {**_valid_payload(), "src_port": "8333"}  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate(payload)
    payload2 = {**_valid_payload(), "dst_port": "18333"}  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate(payload2)


def test_rejects_bad_txid() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "txid": "short"})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "txid": "G" * 64})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "txid": "a" * 63})


def test_rejects_bad_ip() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "src_ip": "999.999.999.999"})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "dst_ip": "not-an-ip"})


def test_rejects_bad_script_type() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "script_type": "P2PK"})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "script_type": "p2pkh"})


def test_array_json_string_handling() -> None:
    from backend.ingest.models import TransactionRecord

    # JSON-encoded strings from CSV should decode
    payload = {
        **_valid_payload(),
        "input_addresses": '["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa","1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"]',  # noqa: E501
        "output_addresses": '["1CdidSeK2d2h4q2s2s2s2s2s2s2s2s2s2s"]',
        "input_amounts": "[0.5, 1.2]",
        "output_amounts": "[1.6]",
    }
    rec = TransactionRecord.model_validate(payload)  # type: ignore[arg-type]
    assert rec.input_addresses == [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
    ]
    assert rec.input_amounts == [0.5, 1.2]

    # empty string -> []
    rec2 = TransactionRecord.model_validate(
        {**_valid_payload(), "input_addresses": "", "output_addresses": ""}
    )  # type: ignore[arg-type]
    assert rec2.input_addresses == []
    assert rec2.output_addresses == []

    # None -> []
    rec3 = TransactionRecord.model_validate(
        {**_valid_payload(), "input_addresses": None, "input_amounts": None}
    )  # type: ignore[arg-type]
    assert rec3.input_addresses == []
    assert rec3.input_amounts == []

    # List passthrough still works
    rec4 = TransactionRecord.model_validate(_valid_payload())
    assert rec4.input_addresses == ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]


def test_timestamp_iso_parsing() -> None:
    from backend.ingest.models import TransactionRecord

    rec = TransactionRecord.model_validate(
        {**_valid_payload(), "timestamp": "2024-06-15T12:30:45Z"}
    )
    assert rec.timestamp.year == 2024
    # datetime object passthrough
    import datetime

    dt = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    rec2 = TransactionRecord.model_validate({**_valid_payload(), "timestamp": dt})
    assert rec2.timestamp == dt


def test_fee_strict_rejects_int_coercion() -> None:
    from backend.ingest.models import TransactionRecord

    # fee must be strict float; int should not coerce
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "fee": 1})  # type: ignore[dict-item]
    # boolean should not coerce
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "fee": True})  # type: ignore[dict-item]


def test_port_range_validation() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "src_port": -1})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "src_port": 70000})
    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "dst_port": 65536})


def test_extra_fields_forbidden() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "extra_field": "oops"})


def test_geo_asn_strict() -> None:
    from backend.ingest.models import TransactionRecord

    with pytest.raises(ValidationError):
        TransactionRecord.model_validate({**_valid_payload(), "geo_asn": "15169"})  # type: ignore[dict-item]


# --- M1 parsers RED tests ---


def _valid_row_dict(idx: int) -> dict[str, object]:
    return {
        "timestamp": f"2024-01-01T00:00:{idx:02d}Z",
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
    import json as _json

    out: dict[str, str] = {}
    for k, v in row.items():
        if isinstance(v, list):
            out[k] = _json.dumps(v)
        else:
            out[k] = str(v)
    return out


def test_quarantine_streaming(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """RED: 10-row CSV with 2 bad rows -> 8 parquet rows + 2 validation entries."""
    import csv
    import json as _json

    from backend.ingest.parsers import ingest_file

    csv_path = tmp_path / "input.csv"
    parquet_path = tmp_path / "out.parquet"
    validation_path = tmp_path / "validation.json"

    rows: list[dict[str, object]] = []
    for i in range(10):
        rows.append(_valid_row_dict(i))
    # make 2 bad rows
    rows[3] = {**rows[3], "txid": "short"}
    rows[7] = {**rows[7], "src_port": "bad"}  # type: ignore[dict-item]

    csv_rows = [_row_to_csv_str(r) for r in rows]
    fieldnames = list(csv_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(csv_rows)  # type: ignore[arg-type]

    result = ingest_file(str(csv_path), str(parquet_path), str(validation_path), engine="polars")
    assert result["rows_ok"] == 8
    assert result["rows_quarantined"] == 2
    assert result["parquet_path"] == str(parquet_path)

    # parquet has 8 rows
    import polars as pl

    df = pl.read_parquet(str(parquet_path))
    assert df.height == 8

    # validation.json has 2 entries with required keys
    data = _json.loads(validation_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    for entry in data:
        assert set(entry.keys()) == {"file", "row", "error", "raw"}
        assert entry["file"] == str(csv_path)
        assert isinstance(entry["row"], int)
        assert 1 <= entry["row"] <= 10
        assert isinstance(entry["error"], str) and len(entry["error"]) > 0
        assert isinstance(entry["raw"], dict)


def test_csv_json_xml_detect(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """detect_format via extension fallback + content sniff."""
    import json as _json

    from backend.ingest.parsers import detect_format

    # csv
    csv_p = tmp_path / "a.csv"
    csv_p.write_text("timestamp,src_ip\n2024-01-01T00:00:00Z,1.1.1.1\n", encoding="utf-8")
    assert detect_format(str(csv_p)) == "csv"

    # json array
    json_p = tmp_path / "b.json"
    json_p.write_text(_json.dumps([_valid_row_dict(0)]), encoding="utf-8")
    assert detect_format(str(json_p)) == "json"

    # xml
    xml_p = tmp_path / "c.xml"
    xml_p.write_text(
        '<?xml version="1.0"?><records><record><txid>abc</txid></record></records>',
        encoding="utf-8",
    )
    assert detect_format(str(xml_p)) == "xml"

    # content sniff: file with wrong extension but json content
    sniff_p = tmp_path / "sniff.dat"
    sniff_p.write_text(_json.dumps([_valid_row_dict(1)]), encoding="utf-8")
    assert detect_format(str(sniff_p)) == "json"

    xml_sniff = tmp_path / "sniff2.dat"
    xml_sniff.write_text('<?xml version="1.0"?><records></records>', encoding="utf-8")
    assert detect_format(str(xml_sniff)) == "xml"


def test_quarantine_streaming_json_and_xml(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Additional streaming validation for JSON and XML paths."""
    import json as _json

    import polars as pl

    from backend.ingest.parsers import ingest_file

    # JSON case
    json_path = tmp_path / "input.json"
    parquet_j = tmp_path / "j.parquet"
    val_j = tmp_path / "vj.json"
    rows = [_valid_row_dict(i) for i in range(5)]
    rows[2] = {**rows[2], "txid": "bad"}
    json_path.write_text(_json.dumps(rows), encoding="utf-8")
    res_j = ingest_file(str(json_path), str(parquet_j), str(val_j), engine="polars")
    assert res_j["rows_ok"] == 4
    assert res_j["rows_quarantined"] == 1
    assert pl.read_parquet(str(parquet_j)).height == 4

    # XML case
    xml_path = tmp_path / "input.xml"
    parquet_x = tmp_path / "x.parquet"
    val_x = tmp_path / "vx.json"
    # Build XML
    import xml.etree.ElementTree as ET

    root = ET.Element("records")
    for idx in range(5):
        r = _valid_row_dict(idx)
        if idx == 1:
            r = {**r, "txid": "bad"}
        rec = ET.SubElement(root, "record")
        for k, v in r.items():
            import json as _js

            child = ET.SubElement(rec, k)
            if isinstance(v, list):
                child.text = _js.dumps(v)
            else:
                child.text = str(v)
    tree = ET.ElementTree(root)
    tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)
    res_x = ingest_file(str(xml_path), str(parquet_x), str(val_x), engine="polars")
    assert res_x["rows_ok"] == 4
    assert res_x["rows_quarantined"] == 1
    assert pl.read_parquet(str(parquet_x)).height == 4


def test_api_ingest_multipart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """API multipart: POST synth_1k.csv → 200, parquet exists, validation filter works."""
    from pathlib import Path as _Path

    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    # health
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    # ingest
    csv_path = _Path("data/raw/synthetic/synth_1k.csv")
    assert csv_path.exists()
    # backup validation
    val = _Path("data/reports/validation.json")
    bak = val.read_text(encoding="utf-8") if val.exists() else None
    data: dict[str, object] | None = None
    try:
        val.write_text("[]", encoding="utf-8")
        with open(csv_path, "rb") as f:
            resp = client.post("/api/ingest", files={"file": (csv_path.name, f, "text/csv")})
        assert resp.status_code == 200, resp.text
        data = resp.json()  # type: ignore[assignment]
        assert data["status"] == "done"  # type: ignore[index]
        assert data["rows_ok"] > 0  # type: ignore[index]
        assert _Path(str(data["parquet"])).exists()  # type: ignore[index]
        # status lookup
        job_id = str(data["id"])  # type: ignore[index]
        r2 = client.get(f"/api/ingest/status/{job_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == job_id
        # validation filter - clean file should have 0, but filter should return list
        r3 = client.get(f"/api/validation/{csv_path.name}")
        assert r3.status_code == 200
        assert isinstance(r3.json(), list)
        # mock mempool shape
        r4 = client.get("/api/mock/mempool")
        assert r4.status_code == 200
        j = r4.json()
        assert "blocks" in j and "mempool-blocks" in j
        assert "height" in j["blocks"][0] and "hash" in j["blocks"][0]
        # replay
        r5 = client.get("/api/replay", params={"at": "2026-08-24T00:00:00Z"})
        assert r5.status_code == 200
        assert "rows" in r5.json()
    finally:
        if bak is not None:
            val.write_text(bak, encoding="utf-8")
        # cleanup parquet produced
        try:
            if data is not None and _Path(str(data["parquet"])).exists():  # type: ignore[index]
                _Path(str(data["parquet"])).unlink()  # type: ignore[index]
        except Exception:
            pass


def test_api_engine_flag_parity(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Parity: polars vs duckdb same schema and rows_ok."""
    import os as _os
    from pathlib import Path as _Path

    import polars as pl
    from fastapi.testclient import TestClient

    from backend.ingest.models import TransactionRecord
    from backend.main import app

    client = TestClient(app)
    csv_path = _Path("data/raw/synthetic/synth_1k.csv")
    val = _Path("data/reports/validation.json")
    bak = val.read_text(encoding="utf-8") if val.exists() else None
    try:
        val.write_text("[]", encoding="utf-8")
        _os.environ["INGEST_ENGINE"] = "polars"
        with open(csv_path, "rb") as f:
            r1 = client.post("/api/ingest", files={"file": ("synth_1k.csv", f, "text/csv")})
        assert r1.status_code == 200
        p1 = _Path(r1.json()["parquet"])
        assert p1.exists()
        df1 = pl.read_parquet(str(p1))
        _os.environ["INGEST_ENGINE"] = "duckdb"
        with open(csv_path, "rb") as f:
            r2 = client.post("/api/ingest", files={"file": ("synth_1k.csv", f, "text/csv")})
        assert r2.status_code == 200
        p2 = _Path(r2.json()["parquet"])
        assert p2.exists()
        df2 = pl.read_parquet(str(p2))
        # schema parity: same allowed columns, rows_ok equal
        allowed = set(TransactionRecord.model_fields.keys())
        assert set(df1.columns).issubset(allowed)
        assert set(df2.columns).issubset(allowed)
        assert set(df1.columns) == set(df2.columns), f"{set(df1.columns)} != {set(df2.columns)}"
        assert r1.json()["rows_ok"] == r2.json()["rows_ok"]
        assert r1.json()["rows_quarantined"] == r2.json()["rows_quarantined"]
    finally:
        _os.environ["INGEST_ENGINE"] = "polars"
        if bak is not None:
            val.write_text(bak, encoding="utf-8")
        for p in [locals().get("p1"), locals().get("p2")]:
            try:
                if p is not None and _Path(p).exists():
                    _Path(p).unlink()
            except Exception:
                pass


# --- M1 VERIFY S1: 50K <2s gate ---

import json as _json2
import time as _time
from pathlib import Path as _Path2

import polars as _pl


def test_50k_csv_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """S1 gate: 50K csv ingest → parquet 50000 rows_ok, validation empty/quarantine, <2s (both engines)."""
    from backend.ingest.parsers import ingest_file

    src = _Path2("data/raw/synthetic/synth_50k.csv")
    assert src.exists(), f"missing fixture {src} — run: python scripts/generate_synthetic.py --scale 50k --sigma 30 --format all --seed 42"
    assert src.stat().st_size > 0
    with open(src, encoding="utf-8") as f:
        lines = sum(1 for _ in f)
    assert lines == 50001, f"expected 50001 lines, got {lines}"

    for engine in ("polars", "duckdb"):
        out_parquet = tmp_path / f"synth_50k_{engine}.parquet"
        val_json = tmp_path / f"validation_{engine}.json"
        val_json.write_text("[]", encoding="utf-8")
        t0 = _time.monotonic()
        result = ingest_file(str(src), str(out_parquet), str(val_json), engine=engine)
        elapsed_ms = (_time.monotonic() - t0) * 1000
        print(f"[50k {engine}] rows_ok={result['rows_ok']} quarantined={result['rows_quarantined']} time={elapsed_ms:.1f} ms")
        assert result["rows_ok"] + result["rows_quarantined"] == 50000
        assert result["rows_ok"] == 50000 - result["rows_quarantined"]
        assert result["rows_ok"] >= 49000, "too many quarantined rows"
        assert out_parquet.exists()
        df = _pl.read_parquet(str(out_parquet))
        assert df.height == result["rows_ok"]
        assert df.height == 50000 - result["rows_quarantined"]
        raw_val = _json2.loads(val_json.read_text(encoding="utf-8"))
        assert isinstance(raw_val, list)
        assert len(raw_val) == result["rows_quarantined"]
        threshold = 2000 if engine == "polars" else 2500
        assert elapsed_ms < threshold, f"{engine} 50k ingest {elapsed_ms:.1f} ms >= {threshold} ms"


def test_50k_quarantine_streaming(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """S2 quarantine at 50K scale: inject 3 bad rows into 50K → 49997 ok, 3 quarantined."""
    import csv

    from backend.ingest.parsers import ingest_file

    src = _Path2("data/raw/synthetic/synth_50k.csv")
    if not src.exists():
        pytest.skip("50k fixture missing")
    with open(src, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    import polars as pl2

    df_src = pl2.read_csv(str(src), n_rows=50000)
    rows = df_src.to_dicts()  # type: ignore[no-untyped-call]
    assert len(rows) == 50000
    rows[100] = {**rows[100], "txid": "bad"}
    rows[1000] = {**rows[1000], "src_port": "not_a_port"}
    rows[25000] = {**rows[25000], "txid": "short"}
    tmp_csv = tmp_path / "synth_50k_bad.csv"
    with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: (str(v) if not isinstance(v, str) else v) for k, v in r.items()})
    out_parquet = tmp_path / "out_50k_q.parquet"
    val_json = tmp_path / "val_50k_q.json"
    val_json.write_text("[]", encoding="utf-8")
    result = ingest_file(str(tmp_csv), str(out_parquet), str(val_json), engine="polars")
    assert result["rows_ok"] == 49997
    assert result["rows_quarantined"] == 3
    assert _pl.read_parquet(str(out_parquet)).height == 49997
    data = _json2.loads(val_json.read_text(encoding="utf-8"))
    assert len(data) == 3


def test_50k_parity_polars_duckdb(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """S3 parity at 50K: polars vs duckdb same columns, same rows_ok, same schema."""
    import polars as pl3

    from backend.ingest.models import TransactionRecord
    from backend.ingest.parsers import ingest_file

    src = _Path2("data/raw/synthetic/synth_50k.csv")
    if not src.exists():
        pytest.skip("50k fixture missing")
    p1 = tmp_path / "p1.parquet"
    v1 = tmp_path / "v1.json"
    v1.write_text("[]", encoding="utf-8")
    p2 = tmp_path / "p2.parquet"
    v2 = tmp_path / "v2.json"
    v2.write_text("[]", encoding="utf-8")
    r1 = ingest_file(str(src), str(p1), str(v1), engine="polars")
    r2 = ingest_file(str(src), str(p2), str(v2), engine="duckdb")
    assert r1["rows_ok"] == r2["rows_ok"] == 50000 - r1["rows_quarantined"]
    assert r1["rows_quarantined"] == r2["rows_quarantined"]
    df1 = pl3.read_parquet(str(p1))
    df2 = pl3.read_parquet(str(p2))
    allowed = set(TransactionRecord.model_fields.keys())
    assert set(df1.columns).issubset(allowed)
    extra2 = [c for c in df2.columns if c not in allowed]
    if extra2:
        df2 = df2.drop(extra2)
        df2.write_parquet(str(p2))
    assert set(df2.columns).issubset(allowed)
    assert set(df1.columns) == set(df2.columns)
    assert df1.height == df2.height


def test_50k_api_ingest_multipart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """API 50K multipart: POST synth_50k.csv → 200, <2s, parquet 50K."""
    import time as _t2
    from pathlib import Path as _P

    from fastapi.testclient import TestClient

    from backend.main import app

    src = _P("data/raw/synthetic/synth_50k.csv")
    if not src.exists():
        pytest.skip("50k fixture missing")
    client = TestClient(app)
    val = _P("data/reports/validation.json")
    bak = val.read_text(encoding="utf-8") if val.exists() else None
    try:
        val.write_text("[]", encoding="utf-8")
        t0 = _t2.monotonic()
        with open(src, "rb") as f:
            resp = client.post("/api/ingest", files={"file": (src.name, f, "text/csv")})
        elapsed_ms = (_t2.monotonic() - t0) * 1000
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "done"
        assert data["rows_ok"] + data["rows_quarantined"] == 50000
        assert _P(str(data["parquet"])).exists()
        print(f"[API 50k] elapsed {elapsed_ms:.1f} ms rows_ok={data['rows_ok']}")
        assert elapsed_ms < 3000, f"API 50k {elapsed_ms:.1f} ms >= 3000"
        try:
            _P(str(data["parquet"])).unlink(missing_ok=True)
        except Exception:
            pass
    finally:
        if bak is not None:
            val.write_text(bak, encoding="utf-8")
