#!/usr/bin/env python3
"""Dump parquet schema for parity diff (polars vs duckdb)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dump parquet schema / parity diff")
    p.add_argument(
        "parquet",
        nargs="?",
        help="parquet path (omit: auto-dump 1k/50k)",
    )
    p.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two parquet files")
    p.add_argument("--out", default=None, help="output json path")
    return p.parse_args()


def dump_schema(parquet_path: str) -> dict[str, object]:
    df = pl.read_parquet(parquet_path)
    schema = {k: str(v) for k, v in df.schema.items()}
    return {
        "path": parquet_path,
        "height": df.height,
        "width": df.width,
        "columns": df.columns,
        "schema": schema,
        "dtypes": [str(d) for d in df.dtypes],
    }


def main() -> None:
    args = parse_args()
    if args.compare:
        a, b = args.compare
        sa = dump_schema(a)
        sb = dump_schema(b)
        diff = {
            "a": sa,
            "b": sb,
            "columns_equal": sa["columns"] == sb["columns"],
            "schema_equal": sa["schema"] == sb["schema"],
            "height_equal": sa["height"] == sb["height"],
            "columns_only_in_a": sorted(set(sa["columns"]) - set(sb["columns"])),  # type: ignore[arg-type]
            "columns_only_in_b": sorted(set(sb["columns"]) - set(sa["columns"])),  # type: ignore[arg-type]
        }
        text = json.dumps(diff, indent=2)
        print(text)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        return

    if args.parquet:
        info = dump_schema(args.parquet)
        text = json.dumps(info, indent=2)
        print(text)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        return

    # default: try common paths
    candidates = [
        "data/clean/parquet/synth_1k.parquet",
        "data/clean/parquet/synth_50k.parquet",
        "/tmp/bench_50k_csv_polars_0.parquet",
    ]
    out: dict[str, object] = {}
    for c in candidates:
        if Path(c).exists():
            out[c] = dump_schema(c)
    if not out:
        print("No parquet found; pass a path explicitly")
        return
    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
