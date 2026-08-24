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
