# Journal — M1-ingest — Per-Turn Progress + Learnings

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

## Turn 1 — 2026-08-24T08:56+05:30 — M1 Ingest complete: models+parsers+api+synthetic+watch/WS/replay+50K<2s (Wave0-6)
Done: backend/ingest/models.py:93 LOC TransactionRecord strict ConfigDict+Field(strict)+field_validator CSV JSON arrays; backend/ingest/parsers.py:395 LOC Polars scan_csv 100K sink_parquet+ijson kvitems+lxml iterparse+quarantine atomic append; backend/api/ingest.py:240 LOC POST /api/ingest multipart+batch+status+validation+mock mempool+replay limit1000 + WS /ws/mock/mempool + watchdog 30s Observer+debounce+dedupe; backend/main.py lifespan auto-watch; scripts/generate_synthetic.py:577 LOC --scale 1k|50k sigma 5/30/120 faker 5K IPs jitter; scripts/bench_ingest.py + dump_parquet_schema.py; data/raw/synthetic/synth_50k.csv 50001 lines 19M + json 37M + xml 41M; data/clean/parquet/synth_50k.parquet 50000 rows; data/reports/validation.json quarantine + ingest_seen.json dedupe; tests/test_ingest.py 22 tests + tests/test_watch_ws.py 3 tests (25 total); Makefile bench + openapi.yaml v1 validated + README INGEST_ENGINE 11 hits hybrid sink 1.1
Learned: Pydantic strict divergence model_validate vs model_validate_json + Field(strict) on int->float still coerces needs custom validator — backend/ingest/models.py:42; Polars sink_parquet requires LazyFrame not eager + json dumps for Object dtype IPv4 — backend/ingest/parsers.py:112; python-magic content sniff fallback needed for XML vs mimetypes text/plain — backend/ingest/parsers.py:34; duckdb COPY drops injection_label needs _normalize_parquet before parity — backend/api/ingest.py:88; watchdog Observer schedule needs poll fallback thread — backend/api/ingest.py:210
Evidence: pytest tests/test_ingest.py tests/test_watch_ws.py -v 25 passed 12.05s (S1 50K polars 1765ms duckdb 1024ms <2s, S2 quarantine 2 rows, S3 parity diff empty); bench.json p50 1771ms <2000 csv PASS (json 1875 xml 2174); TestClient POST /api/ingest 200 rows_ok 50000, GET /api/validation 200, GET /api/mock/mempool 200 keys blocks+mempool-blocks, WS /ws/mock/mempool 101 shape ok, GET /api/replay?at limit 1000 200, GET /api/health 200; ruff backend 0 checks; basedpyright backend 0 errors; openapi.yaml spec-validator OK 9 paths
Next: handoff to M2 (data/clean/parquet/synth_50k.parquet + data/reports/validation.json ready per schema.sql v1 — M2 build.py can read 50K)
Blocked: none
