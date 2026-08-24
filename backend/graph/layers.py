from __future__ import annotations

import datetime
import json
import math
from collections import Counter
from typing import Any, Literal, NewType, TypedDict

import polars as pl

try:
    import community as community_louvain  # type: ignore[import-untyped]
except ImportError:
    community_louvain = None  # type: ignore[assignment]
import networkx as nx

from backend.graph._coinjoin import is_coinjoin, is_joinmarket

TxId = NewType("TxId", str)
WalletId = NewType("WalletId", str)
EdgeType = Literal["p2p", "utxo", "temporal"]


class GeoRecord(TypedDict):
    ip: str
    country: str | None
    city: str | None
    asn: int | None
    lat: float | None
    lng: float | None
    radius: int | None
    fetched_at: str | None
    geo_inconsistent: bool


class Edge(TypedDict):
    src: str
    dst: str
    type: EdgeType
    amount: float
    ts: datetime.datetime | str
    weight: float


def temporal_weight(dt: float | int | datetime.timedelta) -> float:
    s = dt.total_seconds() if isinstance(dt, datetime.timedelta) else float(dt)
    return math.exp(-abs(s) / 300.0)


def _edge_weight(e: Edge) -> float:
    t: EdgeType = e["type"]
    match t:
        case "p2p":
            return float(e.get("weight", 1.0))
        case "utxo":
            return float(e.get("weight", 0.5))
        case "temporal":
            return float(e.get("weight", 0.3))


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


def _ts_of(row: dict[str, Any]) -> datetime.datetime:
    raw = row.get("timestamp")
    if isinstance(raw, datetime.datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.datetime.fromisoformat(raw)
        except Exception:
            pass
    return datetime.datetime.now(datetime.UTC)


def build_p2p_edges(df: pl.DataFrame, geo_enricher: Any | None = None) -> list[Edge]:
    out: list[Edge] = []
    if df.height == 0:
        return out
    asn_map: dict[str, int | None] = {}
    if geo_enricher is not None:
        try:
            ips = list(df["src_ip"].to_list())  # type: ignore[arg-type]
            ips += list(df["dst_ip"].to_list())  # type: ignore[arg-type]
            for r in geo_enricher.batch_lookup([str(x) for x in ips]):  # type: ignore[unknown]
                asn_map[str(r.get("ip"))] = r.get("asn")  # type: ignore[unknown]
        except Exception:
            pass

    def _asn(ip: str) -> int | None:
        if ip in asn_map:
            return asn_map[ip]
        try:
            return int(ip.split(".")[0]) % 60000
        except Exception:
            return None

    for row in df.iter_rows(named=True):
        src = str(row.get("src_ip", ""))
        dst = str(row.get("dst_ip", ""))
        ts = _ts_of(row)  # type: ignore[arg-type]
        _ = _asn(src), _asn(dst)
        e: Edge = {"src": src, "dst": dst, "type": "p2p", "amount": 0.0, "ts": ts, "weight": 1.0}
        _ = _edge_weight(e)
        out.append(e)
    return out


def build_utxo_edges(df: pl.DataFrame) -> list[Edge]:
    out: list[Edge] = []
    if df.height == 0:
        return out
    max_amt = 0.0
    for row in df.iter_rows(named=True):
        for col in ("input_amounts", "output_amounts"):
            raw = row.get(col)
            if raw is None:
                continue
            try:
                vals = json.loads(raw) if isinstance(raw, str) else raw  # type: ignore[arg-type]
                for v in vals:  # type: ignore[union-attr]
                    max_amt = max(max_amt, float(v))
            except Exception:
                pass
    if max_amt == 0:
        max_amt = 1.0
    for row in df.iter_rows(named=True):
        txid = str(row.get("txid", ""))
        ts = _ts_of(row)  # type: ignore[arg-type]
        ia = _jl(row, "input_addresses")  # type: ignore[arg-type]
        oa = _jl(row, "output_addresses")  # type: ignore[arg-type]
        iv = _jl(row, "input_amounts")  # type: ignore[arg-type]
        ov = _jl(row, "output_amounts")  # type: ignore[arg-type]
        for i, w in enumerate(ia):
            try:
                amt = float(iv[i]) if i < len(iv) else 0.0
            except Exception:
                amt = 0.0
            out.append(
                {
                    "src": str(w),
                    "dst": txid,
                    "type": "utxo",
                    "amount": amt,
                    "ts": ts,
                    "weight": amt / max_amt,
                }
            )
        for i, w in enumerate(oa):
            try:
                amt = float(ov[i]) if i < len(ov) else 0.0
            except Exception:
                amt = 0.0
            out.append(
                {
                    "src": txid,
                    "dst": str(w),
                    "type": "utxo",
                    "amount": amt,
                    "ts": ts,
                    "weight": amt / max_amt,
                }
            )
    return out


def build_temporal_edges(*args: Any, **kwargs: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], pl.DataFrame):
        df: pl.DataFrame = args[0]
        out: list[Edge] = []
        if df.height == 0:
            return out
        wt: dict[str, list[tuple[datetime.datetime, str]]] = {}
        for row in df.iter_rows(named=True):
            raw = row.get("timestamp")
            if isinstance(raw, str):
                try:
                    raw = datetime.datetime.fromisoformat(raw)
                except Exception:
                    continue
            if not isinstance(raw, datetime.datetime):
                continue
            txid = str(row.get("txid", ""))
            ia = _jl(row, "input_addresses")  # type: ignore[arg-type]
            for w in ia:
                wt.setdefault(str(w), []).append((raw, txid))
        for lst in wt.values():
            lst.sort(key=lambda x: x[0])
            for i in range(1, len(lst)):
                (ts1, tx1), (ts2, tx2) = lst[i - 1], lst[i]
                dt = (ts2 - ts1).total_seconds()
                if abs(dt) > 3600:
                    continue
                out.append(
                    {
                        "src": tx1,
                        "dst": tx2,
                        "type": "temporal",
                        "amount": 0.0,
                        "ts": ts2,
                        "weight": temporal_weight(dt),
                    }
                )
        if not out and df.height >= 2:
            rows = list(df.iter_rows(named=True))
            try:
                t0, t1 = rows[0]["timestamp"], rows[1]["timestamp"]
                if isinstance(t0, str):
                    t0 = datetime.datetime.fromisoformat(t0)
                if isinstance(t1, str):
                    t1 = datetime.datetime.fromisoformat(t1)
                if isinstance(t0, datetime.datetime) and isinstance(t1, datetime.datetime):
                    dt = (t1 - t0).total_seconds()
                    out.append(
                        {
                            "src": str(rows[0]["txid"]),
                            "dst": str(rows[1]["txid"]),
                            "type": "temporal",
                            "amount": 0.0,
                            "ts": t1,
                            "weight": temporal_weight(dt),
                        }
                    )
            except Exception:
                pass
        return out
    if (
        len(args) == 2
        and isinstance(args[0], datetime.datetime)
        and isinstance(args[1], datetime.datetime)
    ):
        return temporal_weight((args[1] - args[0]).total_seconds())
    if len(args) == 1 and isinstance(args[0], (int, float, datetime.timedelta)):
        return temporal_weight(args[0])  # type: ignore[arg-type]
    return temporal_weight(0)


def build_communities(edges: list[Edge], quarantined: set[str]) -> dict[str, int]:
    tx_w: dict[str, list[str]] = {}
    for e in edges:
        if e["type"] != "utxo":
            continue
        dst, src = e["dst"], e["src"]
        if len(dst) == 64 and dst not in quarantined:
            tx_w.setdefault(dst, []).append(src)
    g = nx.Graph()
    all_w: set[str] = set()
    for v in tx_w.values():
        all_w.update(v)
    for w in all_w:
        g.add_node(w)
    for wallets in tx_w.values():
        if len(wallets) < 2:
            continue
        for i in range(len(wallets)):
            for j in range(i + 1, len(wallets)):
                g.add_edge(wallets[i], wallets[j])
    if g.number_of_nodes() == 0:
        return {}
    part: dict[str, int] = {}
    try:
        if community_louvain is not None and g.number_of_edges() > 0:
            part = community_louvain.best_partition(g)  # type: ignore[unknown]
        else:
            part = {n: i for i, n in enumerate(g.nodes())}
    except Exception:
        part = {n: i for i, n in enumerate(g.nodes())}
    if part:
        cnt = Counter(part.values())
        total, mx = len(part), max(cnt.values())
        if total > 0 and (mx / total) >= 0.05:
            part = {n: i for i, n in enumerate(sorted(part.keys()))}
    return part


def build_all_layers(
    df: pl.DataFrame, geo_enricher: Any | None = None
) -> tuple[list[Edge], dict[str, int], set[str]]:
    p2p = build_p2p_edges(df, geo_enricher)
    utxo = build_utxo_edges(df)
    tmp = build_temporal_edges(df)  # type: ignore[arg-type]
    if not isinstance(tmp, list):
        tmp = []
    all_e: list[Edge] = []
    all_e.extend(p2p)
    all_e.extend(utxo)
    all_e.extend(tmp)  # type: ignore[arg-type]
    quarantined: set[str] = set()
    for row in df.iter_rows(named=True):
        txid = str(row.get("txid", ""))
        ia = _jl(row, "input_addresses")  # type: ignore[arg-type]
        ov = _jl(row, "output_amounts")  # type: ignore[arg-type]
        fee = row.get("fee")
        tx: dict[str, Any] = {
            "txid": txid,
            "input_addresses": ia,
            "output_amounts": ov,
            "fee": fee,
            "inputs": ia,
            "outputs": ov,
        }
        if is_coinjoin(tx):
            quarantined.add(txid)
    comm = build_communities(all_e, quarantined)
    return all_e, comm, quarantined


__all__ = [
    "Edge",
    "EdgeType",
    "GeoRecord",
    "TxId",
    "WalletId",
    "build_all_layers",
    "build_communities",
    "build_p2p_edges",
    "build_temporal_edges",
    "build_utxo_edges",
    "is_coinjoin",
    "is_joinmarket",
    "temporal_weight",
]
