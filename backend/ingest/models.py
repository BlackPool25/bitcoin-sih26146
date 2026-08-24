"""Pydantic v2 strict TransactionRecord for M1 ingest (PROTOTYPE_DECISIONS_FINAL §2 Part1)."""

from __future__ import annotations

import json
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionRecord(BaseModel):
    """Strict validated Bitcoin transaction + P2P envelope."""

    model_config = ConfigDict(strict=True, extra="forbid")

    timestamp: datetime
    src_ip: IPv4Address
    dst_ip: IPv4Address
    src_port: int = Field(ge=0, le=65535, strict=True)
    dst_port: int = Field(ge=0, le=65535, strict=True)
    txid: str = Field(pattern=r"^[a-f0-9]{64}$", strict=True)
    input_addresses: list[str]
    output_addresses: list[str]
    input_amounts: list[float]
    output_amounts: list[float]
    fee: float = Field(strict=True)
    script_type: Literal["P2PKH", "P2SH", "P2WPKH", "P2WSH", "unknown"]
    geo_country: str
    geo_asn: int = Field(strict=True)

    @field_validator("src_ip", "dst_ip", mode="before")
    @classmethod
    def _parse_ip(cls, v: Any) -> Any:
        if isinstance(v, IPv4Address):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return v
            try:
                return IPv4Address(s)
            except ValueError:
                return v
        return v

    @field_validator("fee", mode="before")
    @classmethod
    def _strict_fee(cls, v: Any) -> Any:
        # Pydantic strict float still accepts int (1 -> 1.0); enforce true strict.
        if isinstance(v, bool):
            return v  # let Pydantic raise float_type
        if isinstance(v, int) and not isinstance(v, float):
            raise ValueError("fee must be float (strict, int not allowed)")
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, v: Any) -> Any:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return v
            # Handle Zulu suffix: 2024-01-01T00:00:00Z -> +00:00
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return v
        return v

    @field_validator(
        "input_addresses",
        "output_addresses",
        "input_amounts",
        "output_amounts",
        mode="before",
    )
    @classmethod
    def _parse_json_list(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            if v == "":
                return []
            stripped = v.strip()
            if stripped == "":
                return []
            # Only attempt JSON parsing if it looks like a JSON array;
            # otherwise treat empty string already handled and let strict validation fail.
            if stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    return v
            # Spec says: if value is str -> json.loads(value); handle "" -> []
            # so try generic parse for non-bracket strings as well
            try:
                parsed = json.loads(stripped)
                return parsed
            except json.JSONDecodeError:
                return v
        return v


def validate_record(raw: dict[str, Any]) -> TransactionRecord:
    """Validate raw dict strictly into TransactionRecord."""
    return TransactionRecord.model_validate(raw)
