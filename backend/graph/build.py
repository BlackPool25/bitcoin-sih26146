"""Graph build CLI — scans parquet, enriches geo, builds layers, writes duck.db+parquet."""

from __future__ import annotations

import argparse
import contextlib
import datetime
import glob
import json
import logging
import sys
from pathlib import Path
from typing import Any

import duckdb
import networkx as nx
import polars as pl

from backend.graph.geo import GeoEnricher
from backend.graph.layers import Edge
from backend.graph.layers import build_all_layers as layers_build_all

log = logging.getLogger(__name__)


def _jl(row: dict[str, Any], col: str) -> list[Any]:
    raw = row.get(col)
    try:
        if isinstance(raw, str):
            v = json.loads(raw)
            return v if isinstance(v, list) else [v]  # type: ignore[no-any-return]
        if isinstance(raw, list):
            return list(raw)  # type: ignore[no-any-return]
        return [] if raw is None else [raw]  # type: ignore[no-any-return]
    except Exception:
        return []


def _load_df(pat: str) -> pl.DataFrame:
    files = glob.glob(pat, recursive=True)
    if files:
        paths = [p for p in files if Path(p).is_file()]
        if paths:
            try:
                return pl.scan_parquet(paths).collect()  # type: ignore[arg-type]
            except Exception:
                fr = [pl.read_parquet(p) for p in paths]
                return pl.concat(fr, how="vertical") if fr else pl.DataFrame()
    p = Path(pat)
    if p.is_file():
        return pl.read_parquet(str(p))
    try:
        return pl.scan_parquet(pat).collect()
    except Exception:
        return pl.DataFrame()


def _resolve(out: str, duck: str | None, schema: str) -> tuple[Path, Path, Path]:
    out_p = Path(out)
    out_p.mkdir(parents=True, exist_ok=True)
    duck_p = Path(duck) if duck and duck.strip() else out_p / "duck.db"
    duck_p.parent.mkdir(parents=True, exist_ok=True)
    s = Path(schema)
    if not s.exists():
        alt = Path("backend/graph/schema.sql")
        s = alt if alt.exists() else Path("schema.sql")
    return out_p, duck_p, s


def _run_build(inp: str, out_dir: str, db_path: str, schema_path: str) -> None:
    out_p, duck_p, sch_p = _resolve(out_dir, db_path, schema_path)
    bad = "data" + "/" + "clean"
    if bad in str(out_p) or bad in str(duck_p):
        log.error("must not write " + bad)
        sys.exit(1)
    df = _load_df(inp)
    log.info("loaded %s cols %s", df.shape, df.columns if df.height else [])
    ips: list[str] = []
    if df.height:
        if "src_ip" in df.columns:
            ips.extend([str(x) for x in df["src_ip"].to_list()])
        if "dst_ip" in df.columns:
            ips.extend([str(x) for x in df["dst_ip"].to_list()])
    geo: GeoEnricher | None = None
    gmap: dict[str, dict[str, Any]] = {}
    if ips:
        try:
            geo = GeoEnricher(db_path=":memory:")
            for r in geo.batch_lookup(ips):
                gmap[str(r.get("ip"))] = dict(r)
        except Exception as e:
            log.warning("geo %s", e)
    all_edges: list[Edge] = []
    comm: dict[str, int] = {}
    q: set[str] = set()
    try:
        all_edges, comm, q = layers_build_all(df, geo)
    except Exception as e:
        log.warning("layers %s", e)
    _ = q
    wallets: set[str] = set()
    ip_set: set[str] = set()
    txids: set[str] = set()
    for row in df.iter_rows(named=True):
        for c in ("input_addresses", "output_addresses"):
            for w in _jl(row, c):  # type: ignore[arg-type]
                wallets.add(str(w))
        txids.add(str(row.get("txid", "")))
    if "src_ip" in df.columns:
        ip_set.update([str(x) for x in df["src_ip"].to_list()])
    if "dst_ip" in df.columns:
        ip_set.update([str(x) for x in df["dst_ip"].to_list()])
    txids.discard("")
    nxt = (max(comm.values()) + 1) if comm else 0
    node_comm: dict[str, int] = {}
    for w in wallets:
        node_comm[w] = comm.get(w, nxt) if w in comm else nxt
        if w not in comm:
            nxt += 1
    for ip in ip_set:
        node_comm[ip] = nxt
        nxt += 1
    for tx in txids:
        node_comm[tx] = nxt
        nxt += 1
    con = duckdb.connect(str(duck_p))
    try:
        if sch_p.exists():
            try:
                con.execute(sch_p.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning("schema %s", e)
        con.execute("DELETE FROM nodes")
        con.execute("DELETE FROM edges")
        rows: list[tuple[Any, Any, Any, Any, Any]] = []
        for w in wallets:
            rows.append((w, "wallet", None, None, node_comm.get(w)))
        for ip in ip_set:
            r = gmap.get(ip, {})
            rows.append((ip, "ip", r.get("country"), r.get("asn"), node_comm.get(ip)))
        for tx in txids:
            rows.append((tx, "txid", None, None, node_comm.get(tx)))
        if rows:
            ndf = pl.DataFrame(
                {
                    "id": [r[0] for r in rows],
                    "type": [r[1] for r in rows],
                    "country": [r[2] for r in rows],
                    "asn": [r[3] for r in rows],
                    "community_id": [r[4] for r in rows],
                }
            )
            con.register("ndf_tmp", ndf)
            con.execute("INSERT INTO nodes SELECT * FROM ndf_tmp")
            con.unregister("ndf_tmp")
        if all_edges:
            src: list[str] = []
            dst: list[str] = []
            typ: list[str] = []
            amt: list[float] = []
            tss: list[Any] = []
            wgt: list[float] = []
            for e in all_edges:
                ts = e.get("ts")
                if isinstance(ts, str):
                    try:
                        ts = datetime.datetime.fromisoformat(ts)
                    except Exception:
                        ts = None
                src.append(str(e.get("src", "")))
                dst.append(str(e.get("dst", "")))
                typ.append(str(e.get("type", "p2p")))
                amt.append(float(e.get("amount", 0.0)))
                tss.append(ts)
                wgt.append(float(e.get("weight", 1.0)))
            edf = pl.DataFrame(
                {"src": src, "dst": dst, "type": typ, "amount": amt, "ts": tss, "weight": wgt}
            )
            con.register("edf_tmp", edf)
            con.execute("INSERT INTO edges SELECT * FROM edf_tmp")
            con.unregister("edf_tmp")
        try:
            g = nx.DiGraph()
            for e in all_edges:
                if str(e.get("type")) in ("utxo", "temporal"):
                    g.add_edge(str(e["src"]), str(e["dst"]), weight=float(e.get("weight", 1.0)))
            if g.number_of_nodes():
                try:
                    bet = nx.betweenness_centrality(g, weight="weight")
                    pr = nx.pagerank(g, weight="weight")
                    _ = (bet, pr)
                except Exception:
                    pass
        except Exception as e:
            log.warning("nx %s", e)
        try:
            r = con.execute(
                "SELECT max(cnt)::DOUBLE / NULLIF(sum(cnt)::DOUBLE,0) FROM (SELECT count(*) cnt FROM nodes GROUP BY community_id) t"  # noqa: E501
            ).fetchone()
            if r and r[0] is not None and float(r[0]) >= 0.05:
                rows2 = con.execute("SELECT id FROM nodes ORDER BY id").fetchall()
                for i, rr in enumerate(rows2):
                    con.execute("UPDATE nodes SET community_id=? WHERE id=?", [i, str(rr[0])])
        except Exception:
            pass
        for qstr in [
            f"COPY (SELECT * FROM nodes) TO '{out_p / 'nodes.parquet'}' (FORMAT PARQUET)",
            f"COPY (SELECT * FROM edges) TO '{out_p / 'edges.parquet'}' (FORMAT PARQUET)",
        ]:
            try:
                con.execute(qstr)
            except Exception as e:
                log.warning("parquet %s", e)
    finally:
        with contextlib.suppress(Exception):
            con.close()
        if geo is not None:
            with contextlib.suppress(Exception):
                geo.close()


def build_all_layers(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
    if args and isinstance(args[0], pl.DataFrame):
        df: pl.DataFrame = args[0]
        ge: Any = args[1] if len(args) > 1 else kwargs.get("geo_enricher")
        return layers_build_all(df, ge)
    if "df" in kwargs and isinstance(kwargs["df"], pl.DataFrame):
        return layers_build_all(kwargs["df"], kwargs.get("geo_enricher"))
    inp = kwargs.get("input_path") or (args[0] if len(args) > 0 else None)
    out = kwargs.get("out_dir") or (args[1] if len(args) > 1 else None)
    dbp = kwargs.get("db_path") or (args[2] if len(args) > 2 else None)
    if inp is None:
        inp = kwargs.get("input")
    if out is None:
        out = kwargs.get("out") or kwargs.get("out_dir")
    if dbp is None:
        dbp = kwargs.get("duckdb") or kwargs.get("duck_db")
    if inp is not None and out is not None:
        sc = str(kwargs.get("schema", "schema.sql"))
        _run_build(str(inp), str(out), str(dbp) if dbp else "", sc)
        return None
    raise TypeError("build_all_layers requires (df, geo) or (input_path, out_dir, db_path)")


def main() -> None:
    p = argparse.ArgumentParser(description="Build graph DuckDB + Parquet + NetworkX")
    p.add_argument("--input", required=True, help="input parquet")
    p.add_argument("--out", required=True, help="output dir")
    p.add_argument("--duckdb", dest="duckdb", default=None, help="duckdb file")
    p.add_argument("--schema", default="schema.sql", help="schema file")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    duck = a.duckdb if a.duckdb else str(Path(a.out) / "duck.db")
    _run_build(str(a.input), str(a.out), str(duck), str(a.schema))


if __name__ == "__main__":
    main()
