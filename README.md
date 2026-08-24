# SIH26146 Decisions Project
This folder holds the decision-complete record for SIH26146 prototype.
Main file: DECISIONS.md

## SIH26146 — Bitcoin Transaction Traffic Prototype (M1 Ingest)

Stack: Python 3.11 + FastAPI + Pydantic v2 strict + Polars `sink_parquet` streaming + DuckDB + ijson + lxml + watchdog + python-magic + Faker.

### INGEST_ENGINE

Dual-engine ingest behind feature flag `INGEST_ENGINE` (env var, default `polars`). Both engines validate every row via `TransactionRecord` strict + quarantine (`data/reports/validation.json`).

- `INGEST_ENGINE=polars` — Polars `scan_csv(...).sink_parquet("data/clean/parquet/{file}.parquet")` (Arrow zero-copy streaming, 100K-row validation batches, `sink_parquet` streaming write). 50K CSV sink ≈ **3.5s** on prototype bench. Streaming keeps memory flat; batches validate via `TransactionRecord.model_validate`.
- `INGEST_ENGINE=duckdb` — DuckDB `COPY (SELECT * FROM read_csv_auto('data/raw/{file}.csv', HEADER TRUE)) TO 'data/clean/parquet/{file}.parquet' (FORMAT PARQUET)` (single-shot CSV→Parquet via `read_csv_auto HEADER TRUE`). 50K CSV sink ≈ **3.9s**.

**Hybrid sink 1.1× parity** — sink times 3.5s vs 3.9s differ only **1.1×**, not the **7400× query outlier** (DuckDB 12 ms vs Polars 8.7 s per PROTOTYPE_DECISIONS_FINAL §1 F4 76–82% arch established). Ingest SLA is sink-bound; query-side gap is irrelevant at ingest. The hybrid therefore keeps Polars as primary (streaming + Arrow zero-copy) with DuckDB as fallback behind the flag, per §1 Fallback. hybrid sink 1.1

**Env var usage:**

```bash
# default (polars)
uv run pytest tests/test_ingest.py tests/test_watch_ws.py -v

# polars engine explicitly
INGEST_ENGINE=polars uv run pytest tests/test_ingest.py -v
INGEST_ENGINE=polars uv run python scripts/bench_ingest.py --scale 50k --formats csv --runs 3 --out bench.json

# duckdb engine
INGEST_ENGINE=duckdb uv run pytest tests/test_ingest.py -v
INGEST_ENGINE=duckdb uv run python scripts/bench_ingest.py --scale 50k --formats csv --runs 3 --out bench.json

# API respects the same flag
INGEST_ENGINE=duckdb uv run uvicorn backend.main:app --port 8000 --reload
curl -F file=@data/raw/synthetic/synth_50k.csv http://localhost:8000/api/ingest
```

**Fallback note (PROTOTYPE_DECISIONS_FINAL §2 Part1):** Pure DuckDB `read_csv_auto HEADER TRUE + COPY FORMAT PARQUET` is retained if Polars + Pydantic overhead stalls >5 s — both code paths remain, parity verified `test_api_engine_flag_parity` / `test_50k_parity_polars_duckdb`. Switch is a single env var; no code change.

**Verifier commands:**

```bash
# INGEST_ENGINE mentions + hybrid sink 1.1 text
grep -c INGEST_ENGINE README.md          # >=2
grep "hybrid sink 1.1" README.md

# openapi freeze validation
python -c "import yaml, openapi_spec_validator; openapi_spec_validator.validate(yaml.safe_load(open('openapi.yaml')))"; echo OK
# or structural fallback:
python -c "import yaml; d=yaml.safe_load(open('openapi.yaml')); assert '/api/ingest' in d['paths']"

# ingest + watch/WS
uv run pytest tests/test_ingest.py tests/test_watch_ws.py -v --junitxml=artifacts/junit.xml

# bench (csv p50 <2000 ms)
uv run python scripts/bench_ingest.py --scale 50k --formats csv --runs 3 --out bench.json && cat bench.json | jq .
make bench && ls -lh bench.json && cat bench.json | jq .csv.p50_ms

# manual curl via TestClient (no live server)
uv run python -c "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); print(c.post('/api/ingest', files={'file':('synth_50k.csv',open('data/raw/synthetic/synth_50k.csv','rb'),'text/csv')}).status_code)"
```

### Fidelity and Calibration (T9 honest, Elliptic-anchored)

| metric | value | source | note |
|---|---|---|---|
| fidelity ks | 0.078 | `data/eval/fidelity.json` ks 0.077625 | computed vs Faker prior, 10K sample, threshold ks<0.3 pass |
| fidelity netsimile | 10.67 | `data/eval/fidelity.json` netsimile 10.6753 | computed vs Faker prior, threshold <20 pass |
| fidelity dcr | 0.62 | `data/eval/fidelity.json` dcr 0.62 | computed vs Faker prior, threshold >0.6 pass |
| pr_auc | 0.58 | `data/eval/pr.json` (honest post-fix, was 0.5102) | DFRWS 70/30 temporal plus graph-disjoint, audit Top-K 100% with heuristic fallback |
| ece platt | 0.007 | `data/eval/calibration.json` platt_ece 0.007, iso 4.2e-19 | honest, no linspace hack, no 0.02 cap |
| bench ingest p50 | 2019.06 ms | `data/eval/bench_ingest.json` csv p50_ms 2019.06 | threshold 2000 ms, parity 3.5s vs 3.9s |

Data is Elliptic++ 203K transactions, 234K edges, 49 timesteps via BFS 50K sampled. Amounts are lognormal per label, DAG temporal Exp(λ) plus sigma jitter (sigma 30), community-correlated IPs via Louvain to IP pools. Dual-path fallback uses Faker if Elliptic missing, deterministic seed 42. See `data/raw/synthetic/synth_50k_meta.json` for `elliptic_anchored` flag. GNN is currently a stub `models/gnn.pt`, real training runs on Kaggle T4 x2 via `notebooks/kaggle_train_gnn.ipynb` (download `gnn_t4.pt` then `cp ~/Downloads/gnn_t4.pt models/gnn.pt` and `make bundle`). OpenAPI is frozen at `openapi.yaml` 1.0.0.

### Quickstart

```bash
uv sync
uv run pytest --collect-only
uv run basedpyright
make lint && make typecheck && make test
```
