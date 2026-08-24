#!/usr/bin/env python3
"""Generate minimal synthetic parquet mimicking M1 data/clean/parquet/* for TDD isolation."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

SCRIPT_TYPES = ["P2PKH", "P2SH", "P2WPKH", "P2WSH", "unknown"]
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
GEO_WALLET = "1GeoInconsistentWallet"
PEEL_WALLETS = ["1PeelChainA", "1PeelChainB"]


def random_ipv4(rng: random.Random) -> str:
    # Avoid 0.x, 127.x, 224+ multicast etc — just generate plausible public IPs
    return (
        f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    )


def random_txid(rng: random.Random) -> str:
    # 64 hex chars deterministic from rng
    return format(rng.getrandbits(256), "064x")


def random_address(rng: random.Random, prefix: str = "1") -> str:
    # Bitcoin-ish length 26-35, base58
    length = rng.randint(26, 35)
    # ensure prefix char compatible
    body_len = length - len(prefix)
    body = "".join(rng.choices(BASE58, k=body_len))
    return prefix + body


def gen_base_row(rng: random.Random, ts: datetime, ip_pool: list[str]) -> dict:
    n_in = rng.randint(1, 3)
    n_out = rng.randint(1, 3)
    in_addrs = [random_address(rng) for _ in range(n_in)]
    out_addrs = [random_address(rng) for _ in range(n_out)]
    # amounts: 0.001 .. 5 BTC
    in_amts = [round(rng.uniform(0.001, 5.0), 8) for _ in range(n_in)]
    out_amts = [round(rng.uniform(0.001, 5.0), 8) for _ in range(n_out)]
    fee = round(rng.uniform(0.00001, 0.001), 8)
    return {
        "timestamp": ts,
        "src_ip": rng.choice(ip_pool),
        "dst_ip": rng.choice(ip_pool),
        "src_port": rng.randint(0, 65535),
        "dst_port": rng.randint(0, 65535),
        "txid": random_txid(rng),
        "input_addresses": json.dumps(in_addrs),
        "output_addresses": json.dumps(out_addrs),
        "input_amounts": json.dumps(in_amts),
        "output_amounts": json.dumps(out_amts),
        "fee": fee,
        "script_type": rng.choice(SCRIPT_TYPES),
    }


def make_coinjoin_row(rng: random.Random, ts: datetime, src_ip: str, dst_ip: str) -> dict:
    n = 22
    in_addrs = [random_address(rng) for _ in range(n)]
    out_addrs = [random_address(rng) for _ in range(n)]
    # all outputs equal 0.01 BTC, fee small
    in_amts = [round(0.0101, 8) for _ in range(n)]
    out_amts = [round(0.01, 8) for _ in range(n)]
    fee = round(0.0022, 8)  # n*(0.0101-0.01)=0.0022
    return {
        "timestamp": ts,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": rng.randint(0, 65535),
        "dst_port": rng.randint(0, 65535),
        "txid": random_txid(rng),
        "input_addresses": json.dumps(in_addrs),
        "output_addresses": json.dumps(out_addrs),
        "input_amounts": json.dumps(in_amts),
        "output_amounts": json.dumps(out_amts),
        "fee": fee,
        "script_type": rng.choice(SCRIPT_TYPES),
    }


def make_geo_row(rng: random.Random, ts: datetime, src_ip: str, wallet: str) -> dict:
    # single-input wallet to guarantee appearance
    in_addrs = [wallet]
    out_addrs = [random_address(rng)]
    in_amts = [round(rng.uniform(0.1, 2.0), 8)]
    out_amts = [round(in_amts[0] * rng.uniform(0.8, 0.99), 8)]
    fee = round(in_amts[0] - out_amts[0], 8)
    if fee < 0.00001:
        fee = 0.00001
    return {
        "timestamp": ts,
        "src_ip": src_ip,
        "dst_ip": random_ipv4(rng),
        "src_port": rng.randint(0, 65535),
        "dst_port": rng.randint(0, 65535),
        "txid": random_txid(rng),
        "input_addresses": json.dumps(in_addrs),
        "output_addresses": json.dumps(out_addrs),
        "input_amounts": json.dumps(in_amts),
        "output_amounts": json.dumps(out_amts),
        "fee": fee,
        "script_type": rng.choice(SCRIPT_TYPES),
    }


def make_peel_pair(
    rng: random.Random, ts1: datetime, ts2: datetime, wallet: str
) -> tuple[dict, dict]:
    """Create 2-tx peel chain: tx1 output address becomes tx2 input."""
    # tx1: 1 input (wallet), 2 outputs (small peel + change)
    peel_addr = random_address(rng)
    change_addr = random_address(rng)
    tx1_in_amt = round(rng.uniform(1.0, 5.0), 8)
    peel_amt = round(tx1_in_amt * 0.1, 8)
    change_amt = round(tx1_in_amt - peel_amt - 0.0001, 8)
    tx1 = {
        "timestamp": ts1,
        "src_ip": random_ipv4(rng),
        "dst_ip": random_ipv4(rng),
        "src_port": rng.randint(0, 65535),
        "dst_port": rng.randint(0, 65535),
        "txid": random_txid(rng),
        "input_addresses": json.dumps([wallet]),
        "output_addresses": json.dumps([peel_addr, change_addr]),
        "input_amounts": json.dumps([tx1_in_amt]),
        "output_amounts": json.dumps([peel_amt, change_amt]),
        "fee": 0.0001,
        "script_type": rng.choice(SCRIPT_TYPES),
    }
    # tx2: spend change output
    peel2 = random_address(rng)
    change2 = random_address(rng)
    peel_amt2 = round(change_amt * 0.1, 8)
    change_amt2 = round(change_amt - peel_amt2 - 0.0001, 8)
    tx2 = {
        "timestamp": ts2,
        "src_ip": random_ipv4(rng),
        "dst_ip": random_ipv4(rng),
        "src_port": rng.randint(0, 65535),
        "dst_port": rng.randint(0, 65535),
        "txid": random_txid(rng),
        "input_addresses": json.dumps([change_addr]),
        "output_addresses": json.dumps([peel2, change2]),
        "input_amounts": json.dumps([change_amt]),
        "output_amounts": json.dumps([peel_amt2, change_amt2]),
        "fee": 0.0001,
        "script_type": rng.choice(SCRIPT_TYPES),
    }
    return tx1, tx2


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate M2 fixture parquet")
    parser.add_argument(
        "--out", type=str, default="tests/fixtures/m2_small.parquet", help="Output parquet path"
    )
    parser.add_argument("--rows", type=int, default=500, help="Number of rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    rows = args.rows
    base_ts = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    # 5K unique IP pool
    ip_pool_set: set[str] = set()
    while len(ip_pool_set) < 5000:
        ip_pool_set.add(random_ipv4(rng))
    ip_pool = list(ip_pool_set)

    # Generate base rows
    data: list[dict] = []
    for i in range(rows):
        ts = base_ts + timedelta(hours=i)
        # add small jitter seconds to avoid exact collisions but keep hour spacing
        ts = ts + timedelta(seconds=rng.randint(0, 300))
        data.append(gen_base_row(rng, ts, ip_pool))

    # Inject 3 CoinJoin txs at indices 10,11,12
    for idx, offset in enumerate([10, 11, 12]):
        ts = base_ts + timedelta(hours=offset, seconds=rng.randint(0, 300))
        data[offset] = make_coinjoin_row(rng, ts, random_ipv4(rng), random_ipv4(rng))

    # Inject 1 wallet "1GeoInconsistentWallet" with 2 txs at indices 20,21 with distant IPs
    # Requirement: same input_address appears twice with distant IPs 1.1.1.1 (US) and 2.2.2.2 (RU)
    geo_ips = ["1.1.1.1", "2.2.2.2"]
    for j, offset in enumerate([20, 21]):
        ts = base_ts + timedelta(hours=offset, seconds=rng.randint(0, 300))
        data[offset] = make_geo_row(rng, ts, geo_ips[j], GEO_WALLET)

    # Inject 2 peel chains: 4 txs total at indices 30,31 and 32,33
    for chain_idx, wallet in enumerate(PEEL_WALLETS):
        base_offset = 30 + chain_idx * 2
        ts1 = base_ts + timedelta(hours=base_offset, seconds=rng.randint(0, 300))
        ts2 = base_ts + timedelta(hours=base_offset + 1, seconds=rng.randint(0, 300))
        tx1, tx2 = make_peel_pair(rng, ts1, ts2, wallet)
        data[base_offset] = tx1
        data[base_offset + 1] = tx2

    # Verify txid uniqueness
    txids = [r["txid"] for r in data]
    if len(set(txids)) != len(txids):
        # regenerate colliding ones
        seen: set[str] = set()
        for r in data:
            while r["txid"] in seen:
                r["txid"] = random_txid(rng)
            seen.add(r["txid"])

    # Build polars DataFrame with explicit schema to ensure 12 cols
    df = pl.DataFrame(
        data,
        schema={
            "timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
            "src_ip": pl.Utf8,
            "dst_ip": pl.Utf8,
            "src_port": pl.Int64,
            "dst_port": pl.Int64,
            "txid": pl.Utf8,
            "input_addresses": pl.Utf8,
            "output_addresses": pl.Utf8,
            "input_amounts": pl.Utf8,
            "output_amounts": pl.Utf8,
            "fee": pl.Float64,
            "script_type": pl.Utf8,
        },
    )

    # Ensure shape
    assert df.height == rows, f"expected {rows} rows got {df.height}"
    assert df.width == 12, f"expected 12 cols got {df.width}"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(out), compression="zstd", row_group_size=100_000)
    print(f"Wrote {df.shape} to {out} (compression=zstd, row_group=100k)")
    # quick stats
    print(df.head(3))

    # Verify CoinJoin candidates
    # input_addresses JSON array length >=20
    import json as _json

    cj_count = sum(1 for r in data if len(_json.loads(r["input_addresses"])) >= 20)
    print(f"CoinJoin candidates (inputs>=20): {cj_count}")
    geo_count = sum(1 for r in data if GEO_WALLET in r["input_addresses"])
    print(f"Geo wallet occurrences: {geo_count}")


if __name__ == "__main__":
    main()
