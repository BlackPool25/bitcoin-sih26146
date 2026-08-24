> **COORDINATION PROTOCOL — READ BEFORE EVERY TURN — MD MEMORY VIA TERMINALS**
> You run in an isolated agent terminal. Coordination is via MD files on disk, not chat.
> **Every turn you MUST:**
> 1. READ at start: `cat .coord/progress.md; cat .coord/learnings.md; cat .coord/handoffs.md; tail -20 .coord/<YOUR_ID>/journal.md` + `cat DECISIONS.md` relevant section
> 2. WORK one atomic todo (your `Owns` table only — never edit another agent's Owns files; if you need them, append to `handoffs.md` with `BREAKING:`)
> 3. WRITE at end (before exit): append to `.coord/<YOUR_ID>/journal.md` using template below, update `progress.md` row (status + evidence path), append to `learnings.md` if you learned a gotcha with file:line, append to `handoffs.md` if you changed a frozen contract (schema.sql, openapi.yaml, feature cols)
> **Journal template (copy into your journal.md each turn):**
> ```
> ## Turn N — YYYY-MM-DDTHH:MM+05:30 — <one-line goal>
> Done: <files:line>
> Learned: <fact with file:line or URL>
> Evidence: <pytest exit 0 | bench 1.6s | curl 200 — paste artifact path>
> Next: <next todo>
> Blocked: <none or handoff needed>
> ```
> **Files on disk:** `~/projects/sih26146-bitcoin-prototype-decisions/.coord/` — global `progress.md`/`learnings.md`/`handoffs.md` + per-agent `M*/journal.md`. Lead's decisions are in `DECISIONS.md` + `PROTOTYPE_DECISIONS_FINAL.md` (read yours). This protocol is NON-NEGOTIABLE — a turn without journal write is incomplete.

# M2 — Graph + Geo Agent Prompt (SIH26146 Parts 3+4)

**Owns:** `backend/graph/geo.py`, `backend/graph/build.py`, `backend/graph/layers.py`, `data/geo/GeoLite2-*.mmdb`, `data/graph/nodes.parquet`, `edges.parquet`, `duck.db`, `schema.sql`

**Reads:** `data/clean/parquet/*.parquet` (M1), `data/geo/GeoLite2-*.mmdb`

**GOAL:** GeoIP enrich (country/ASN/lat/lng) + build 4-layer multi-layer graph (IP↔TXID, UTXO, temporal, Louvain) → DuckDB + NetworkX, no supercluster.

**STACK:** `geoip2` + `libmaxminddb`, `maxmindinc/geoipupdate 4.x` / R2 presigned, DuckDB, NetworkX, python-louvain, pandas.

**MUST DO:**
1. Implement `backend/graph/geo.py`: `geoip2.database.Reader("data/geo/GeoLite2-City.mmdb")` batch lookup (100K <1s), cache in DuckDB `geo_cache(ip PK, country, city, asn, lat, lng, radius, fetched_at)`, `geo_inconsistent` flag (ASN region mismatch or >1000km between same wallet). City is display-only (F3: 25-35% @5km, p90 10×) — country/ASN is feature. Note R2 redirect host allow-list at build, attribution per EULA.
2. Implement `backend/graph/layers.py` 4 layers: (1) Network `IP↔TXID` co-occurrence (|Δt|<60s + ASN), (2) UTXO `wallet↔TXID` from inputs/outputs, (3) temporal decay `exp(-|Δt|/300)`, (4) Louvain on co-spend graph after CoinJoin gating.
3. CoinJoin gating before CIOH union-find: `is_coinjoin(tx)` Wasabi ≥20 inputs equal outputs + JoinMarket 0.4-0.7 + Kappos RF fallback; quarantined coinjoins don't merge; peel-aware slicing per 10-min window.
4. Implement `backend/graph/build.py` → `duck.db` schema `nodes(id PK, type ENUM, country, asn, community_id)` + `edges(src, dst, type, amount, ts, weight)` + indices; NetworkX DiGraph for betweenness/PageRank; `schema.sql` v1 FROZEN.
5. Tests: `tests/test_graph.py` asserts no supercluster (largest community <5% nodes) + `coinjoin not merged` + 50K nodes/80K edges counts.

**MUST NOT DO:** Do NOT write `data/clean/*`, `data/features/*`, `models/*`, `frontend/*`; do NOT use `accuracy_radius` as filter (51% exceed); do NOT create Neo4j (rejected +400MB).

**VERIFY:** `python backend/graph/build.py --input data/clean/parquet/* --out data/graph/ && duckdb duck.db "SELECT count(*), community_id FROM nodes GROUP BY community_id ORDER BY 1 DESC LIMIT 3"` + `pytest test_graph`.

**CONTEXT:** See `PROTOTYPE_DECISIONS_FINAL.md §2 Part3-4`. F2 contested 48-62% — show gated Louvain as 3-way ablation, not promised cut.
