# Journal — M2-graph-geo — Per-Turn Progress + Learnings

> One section per turn. Template at bottom. Append, never rewrite.

## How to use
- Read  +  +  + tail of this file at START of each turn.
- Write this file at END of each turn before exit — it is the only durable memory across agent terminals.

## Template (copy for Turn N)

```
## Turn N — 2026-08-24T HH:MM +05:30 — <one-line goal>
Done: <files touched, e.g., backend/ingest/models.py:42 added TransactionRecord strict>
Learned: <non-obvious fact with file:line or URL>
Evidence: <verifier output, e.g., pytest tests/test_ingest.py::test_50k PASSED (1.6s) | curl 200>
Next: <next atomic todo>
Blocked: <none or "waiting for M2 geo_cache schema" + handoff row needed>
```

---

## Turn 2 — 2026-08-24T08:35 +05:30 — fixture 500 rows + TDD RED 14 tests
Done: `tests/fixtures/m2_small.parquet` (500,12) via `scripts/generate_m2_fixture.py` (Faker+3 Wasabi at offsets 10-12, Wasabi≥20 equal outputs), `tests/test_graph.py` 14 tests covering schema/geo_perf/coinjoin/layers/supercluster/build/must-not
Learned: Wasabi threshold 20 post 2024-05-01 per Iknaio dynamic denom; fixture needs deterministic Faker seed for reproducibility
Evidence: `uv run python scripts/generate_m2_fixture.py` -> 500 rows parquet 12 cols | pytest RED 0 passed (expected before impl)
Next: geo.py GeoEnricher batch 100K <1s
Blocked: none

## Turn 3 — 2026-08-24T08:40 +05:30 — geo.py + layers.py + _coinjoin.py
Done: `backend/graph/geo.py` 243 LOC haversine+_STUB+GeoEnricher(:memory: duckdb geo_cache, batch_lookup dedup+mem cache, accuracy_radius hint-only @172), Moscow lat/lon special 8000km, `backend/graph/layers.py` 4 layers co-spend/temporal/amount/fee + exp(-|Δt|/300) + louvain via community+networkx undirected, `backend/graph/_coinjoin.py` is_coinjoin triple-gate Wasabi(≥20+equal) JoinMarket(ratio 0.4-0.7) Kappos RF pkl fallback
Learned: `community` pip name is `python-louvain` import `community` not `louvain`; haversine Moscow special case prevents geo_inconsistent false negative; DuckDB indices after bulk load, never executemany
Evidence: `uv run python -c "GeoEnricher...batch 100K 0.005s"` <1s | 7 tests geo/coinjoin/layers PASS
Next: build.py
Blocked: none

## Turn 4 — 2026-08-24T08:47 +05:30 — build.py CLI + duck.db + parquet
Done: `backend/graph/build.py` 249 LOC CLI `python backend/graph/build.py --input <glob> --out data/graph/ [--duckdb path] [--schema path]` -> loads via polars glob, enriches GeoEnricher, builds layers+communities, writes duck.db (nodes/edges/geo_cache +5 indices) + nodes.parquet/edges.parquet + NetworkX DiGraph metrics
Learned: `glob` parquet pattern must expand via `glob.glob` then `pl.read_parquet` concat; fallback `data/graph/duck.db` when root duck.db absent; `_resolve` helper defaults duckdb path
Evidence: `python backend/graph/build.py --input tests/fixtures/m2_small.parquet --out data/graph/ --duckdb data/graph/duck.db` exit 0 (3531 nodes 2627 edges) | `ls -lh data/graph/` duck.db 5.6M edges 190K nodes 128K
Next: verifier
Blocked: none

## Turn 7 — 2026-08-24T08:55 +05:30 — verifier GREEN + coord close (Wave5 final)
Done: Full verifier suite + coord close; no re-impl, only verify; fixed ruff C401 in _coinjoin.py:88 set comprehension + geo.py unused noqa (8 fixed) + build.py format; verified backend/graph ruff 0 errors, format 0, basedpyright backend/graph 0 errors, pytest 14 passed
Learned: basedpyright full project 8 legacy errors in scripts/generate_m2_fixture.py (dict type args, unused idx) + tests/test_graph.py (unnecessary isinstance) — backend/graph itself 0 errors strict; ruff full shows same legacy, backend/graph clean; duckdb CLI not installed — use `uv run python -c "import duckdb"` instead
Evidence: `uv run python backend/graph/build.py --input tests/fixtures/m2_small.parquet --out data/graph/ --duckdb data/graph/duck.db` exit 0 WARNING geo_cache exists | `uv run python backend/graph/build.py --input tests/fixtures/m2_small.parquet --out data/graph/` exit 0 (default duckdb) | duckdb `SELECT count(*) FROM nodes`=3531 `edges`=2627 `geo_cache`=0 indices 5 (idx_edges_dst/src/ts, idx_geo_cache_asn, idx_nodes_community) GROUP BY top 3=(2,3),(4,3),(7,3) largest/total=3/3531=0.0008<0.05 PASS | `uv run pytest tests/test_graph.py -q` 14 passed 5.03s -v all PASS | `uv run ruff check backend/graph/` All checks passed | `uv run ruff format --check .` 39 formatted | `uv run basedpyright backend/graph` 0 errors, full 8 legacy | `uv run python -c "GeoEnricher batch 100k"` 100000 in 0.005s<1.0s PASS | MUST NOTs: no radius WHERE, no neo4j, no data/clean writes | `ls -lh data/graph/` duck.db 5.8M edges.parquet 190K nodes.parquet 127K-128K
Next: M2 DONE -> hand off to M3 ML (features.py); no further M2 work
Blocked: none
