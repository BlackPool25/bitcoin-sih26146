# SIH26146 Decisions Project
This folder holds the decision-complete record for SIH26146 prototype.
Main file: DECISIONS.md

## SIH26146 — Bitcoin Transaction Traffic Prototype (M1 Ingest)

Stack: Python 3.11 + FastAPI + Pydantic v2 strict + Polars `sink_parquet` streaming + DuckDB + ijson + lxml + watchdog + python-magic + Faker.

### INGEST_ENGINE

Placeholder — full parity note will be documented in T13 (PROTOTYPE_DECISIONS_FINAL §1 F4: Hybrid sink 3.5 vs 3.9s parity 1.1×, not 7400× query outlier; feature-flag `INGEST_ENGINE=polars|duckdb`).

### Quickstart

```bash
uv sync
uv run pytest --collect-only
uv run basedpyright
make lint && make typecheck && make test
```
