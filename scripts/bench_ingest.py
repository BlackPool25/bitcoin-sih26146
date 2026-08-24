#!/usr/bin/env python3
"""Bench ingest_file for csv/json/xml on 50K with runs=3, reports p50_ms, writes bench.json."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bench ingest_file on synthetic fixtures")
    p.add_argument("--scale", default="50k", choices=["1k", "10k", "50k", "80k"])
    p.add_argument("--formats", default="csv", help="comma-separated: csv,json,xml or csv,json,xml")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--engine", default="polars", choices=["polars", "duckdb"])
    p.add_argument("--out", default="bench.json", help="output bench.json path")
    return p.parse_args()


def bench_one(fmt: str, scale: str, runs: int, engine: str) -> dict[str, object]:
    from backend.ingest.parsers import ingest_file

    src = Path(f"data/raw/synthetic/synth_{scale}.{fmt}")
    if not src.exists():
        return {"format": fmt, "scale": scale, "error": f"missing {src}", "p50_ms": None}
    times: list[float] = []
    last_result: dict[str, object] | None = None
    for i in range(runs):
        out_parquet = f"/tmp/bench_{scale}_{fmt}_{engine}_{i}.parquet"
        val_json = f"/tmp/bench_{scale}_{fmt}_{engine}_{i}_validation.json"
        # clear validation
        Path(val_json).write_text("[]", encoding="utf-8")
        t0 = time.monotonic()
        res = ingest_file(str(src), out_parquet, val_json, engine=engine)
        dt_ms = (time.monotonic() - t0) * 1000
        times.append(dt_ms)
        last_result = res  # type: ignore[assignment]
        # cleanup
        try:
            Path(out_parquet).unlink(missing_ok=True)
            Path(val_json).unlink(missing_ok=True)
        except Exception:
            pass
    times_sorted = sorted(times)
    p50 = statistics.median(times_sorted)
    p95 = times_sorted[int(len(times_sorted) * 0.95)] if len(times_sorted) > 1 else times_sorted[0]
    result: dict[str, object] = {
        "format": fmt,
        "scale": scale,
        "engine": engine,
        "runs": runs,
        "times_ms": [round(t, 2) for t in times_sorted],
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "mean_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "rows_ok": last_result.get("rows_ok") if last_result else None,  # type: ignore[union-attr]
        "rows_quarantined": last_result.get("rows_quarantined") if last_result else None,  # type: ignore[union-attr]
    }
    # threshold check
    threshold = 2000 if fmt == "csv" else 2500
    result["threshold_ms"] = threshold
    result["pass"] = p50 < threshold
    return result


def main() -> None:
    args = parse_args()
    fmts = [f.strip() for f in args.formats.split(",") if f.strip()]
    scale: str = str(args.scale)
    runs: int = int(args.runs)
    engine: str = str(args.engine)
    out_path = Path(str(args.out))
    results: dict[str, object] = {"scale": scale, "engine": engine, "runs": runs, "formats": {}}
    all_pass = True
    for fmt in fmts:
        r = bench_one(fmt, scale, runs, engine)
        results["formats"] = results.get("formats", {})  # type: ignore[attr-defined]
        assert isinstance(results["formats"], dict)
        results["formats"][fmt] = r  # type: ignore[index]
        p50v = r.get("p50_ms")
        thr = r.get("threshold_ms")
        ok = r.get("pass")
        rk = r.get("rows_ok")
        print(f"[{fmt}] p50={p50v} ms (thr {thr} ms) pass={ok} rows_ok={rk}")
        if not r.get("pass", False):
            # only fail for csv strictly; json/xml warn
            if fmt == "csv":
                all_pass = False
            else:
                print(
                    f"  warn: {fmt} p50 {r.get('p50_ms')} > {r.get('threshold_ms')} (allowed warn)"
                )
    # also handle single-format compat key
    if len(fmts) == 1:
        fmt0 = fmts[0]
        single = results["formats"][fmt0]  # type: ignore[index]
        results["p50_ms"] = single.get("p50_ms")  # type: ignore[union-attr]
        results["csv"] = single  # compat alias
        results["csv.p50_ms"] = single.get("p50_ms")  # type: ignore[index]
    # write json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    # also write to bench.json in cwd if different
    if out_path.name != "bench.json" and not Path("bench.json").exists():
        Path("bench.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if not all_pass:
        print("BENCH FAIL: csv p50 >= 2000 ms")
    else:
        print("BENCH PASS")


if __name__ == "__main__":
    main()
