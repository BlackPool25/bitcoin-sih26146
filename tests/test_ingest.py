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
