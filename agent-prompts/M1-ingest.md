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

# M1 — Backend Ingest Agent Prompt (SIH26146 Part 1 + 2 assist)

**Owns (EXCLUSIVE — no one else writes these):** `backend/ingest/models.py`, `backend/ingest/parsers.py`, `backend/api/ingest.py`, `data/clean/parquet/*.parquet`, `data/reports/validation.json`, `scripts/generate_synthetic.py` (with M2), `data/raw/synthetic/*`

**Reads:** `data/raw/*.csv|json|xml` (bulk uploads, synthetic fixtures), `openapi.yaml` (API freeze)

**GOAL:** Ingest bulk CSV/JSON/XML with Pydantic strict streaming → validated Parquet + per-file validation report; supports batch upload + folder poll + WS mock + replay. 50K <2s verified.

**STACK:** Python 3.11 + FastAPI + Pydantic v2 strict + Polars `sink_parquet` streaming + ijson + lxml + watchdog + duckdb (fallback)

**MUST DO:**
1. Implement `backend/ingest/models.py`: `TransactionRecord` (timestamp, src_ip/dst_ip IPv4, src_port/dst_port 0-65535, txid hex64, input_addresses/output_addresses List[str], input_amounts/output_amounts List[float], fee float, script_type Literal["P2PKH","P2SH","P2WPKH","P2WSH","unknown"], geo_country str, geo_asn int) with `ConfigDict(strict=True)` + `Field(strict=True)` on numeric; handle array fields as JSON-encoded strings in CSV (e.g. `input_addresses='["1A...","1B..."]'`).
2. Implement `backend/ingest/parsers.py`: auto-detect CSV vs JSON vs XML via `python-magic`/`mimetypes`; Polars `scan_csv(...).sink_parquet()` (100K chunks), ijson `kvitems` streaming, `lxml.etree.iterparse` streaming; quarantine errors to `data/reports/validation.json` as `[{file, row, error, raw}]`.
3. Implement `backend/api/ingest.py`: `POST /api/ingest` (multipart file), `POST /api/ingest/batch` (folder), `GET /api/ingest/status/{id}` + `GET /api/validation/{file}`; feature-flag `INGEST_ENGINE` env (polars|duckdb) — duckdb path: `duckdb.sql("COPY (SELECT * FROM read_csv_auto('data/raw/{f}', HEADER TRUE)) TO 'data/clean/parquet/{f}.parquet' (FORMAT PARQUET)")`.
4. Add `watchdog` folder-watch 30s poll → auto-ingest; WS mock `GET /api/mock/mempool` + `WS /ws/mock/mempool` shape-compatible with mempool.space (`blocks`, `mempool-blocks`); replay `GET /api/replay?at={ISO8601}`.
5. Write tests: `tests/test_ingest.py` must assert 50K CSV (synthetic) round-trip valid + validation report contains quarantined rows + engine flag switches.
6. Document `INGEST_ENGINE` parity note in README (F4: hybrid sink 1.1×, not 7400× query).

**MUST NOT DO:** Do NOT write `data/graph/*`, `duck.db`, `data/features/*`, `data/alerts/*`, `frontend/*`; do NOT add columns outside `TransactionRecord`; do NOT silently coerce Pydantic strict — raise.

**VERIFY:** `python -m pytest tests/test_ingest.py -k "50k <2s"` + `curl -F file=@data/raw/synthetic/synth_50k.csv http://localhost:8000/api/ingest` → 200 + `cat data/reports/validation.json | jq .` ; `make bench` ingest <2s on finale laptop.

**CONTEXT:** Files: see `DECISIONS.md §2 Part 1-2` + `PROTOTYPE_DECISIONS_FINAL.md §2 Part1`. API freeze `openapi.yaml` v1. Offline: no network calls.
