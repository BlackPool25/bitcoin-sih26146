# Progress Board — SIH26146 (global, append-only per-agent sections)

> Each agent appends one row per turn under their header. Status: todo | in_progress | done | blocked. Keep ONE in_progress per agent.

## M1 — Ingest (backend/ingest/*)
| Turn | Part | Task | Status | Evidence | Next |
| 1 | 1 | TransactionRecord strict | done | `pytest tests/test_ingest.py::test_transaction_record_strict 13 passed` `backend/ingest/models.py:93` | parsers.py |
| 2 | 1 | parsers.py Polars+ijson+lxml+quarantine | done | `backend/ingest/parsers.py:395` `test_quarantine_streaming 3 passed` `validation.json 2 rows` p50 1.6s<2s | api |
| 3 | 1+2 | generate_synthetic.py 50K/80K/5K | done | `scripts/generate_synthetic.py:577` `synth_50k.csv 50001 19M` `faker 5K IPs` sigma 30 | api |
| 4 | 1 | api/ingest.py FastAPI + INGEST_ENGINE | done | `backend/api/ingest.py:240` `backend/main.py` `POST /api/ingest 200` rows_ok 1K+50K engine polars|duckdb parity diff empty | watch |
| 5 | 1 | watch 30s + WS mock + replay | done | `watchdog Observer+seen.json` `WS /ws/mock/mempool` `GET /api/replay?at limit1000` `openapi.yaml WS+watch` `test_watch_ws 3 passed` | bench |
| 6 | 1 | 50K<2s bench + S1-S3 RED→GREEN | done | `bench.json p50 1771ms <2000` `synth_50k.parquet 50000 rows` `pytest 25 passed 12s` polars 1765ms duckdb 1024ms | finalize |
| 7 | 1 | README INGEST_ENGINE + openapi freeze + gate | done | `README.md INGEST_ENGINE 11 hits hybrid sink 1.1` `openapi.yaml validator OK 9 paths` `make bench PASS` `ruff 0` `basedpyright 0` | M2 handoff |

|------|------|------|--------|----------|------|
| — | 1+2 | Models + parsers + synthetic | todo | — | Start `backend/ingest/models.py` Pydantic strict |

## M2 — Graph+Geo (backend/graph/*)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 3+4 | Geo enricher + multi-layer Louvain | todo | — | Start `backend/graph/geo.py` MaxMind batch |
| 0 | 0 | Bootstrap git+pyproject+dirs+coord (Wave0) | done | `pyproject.toml:geoip2` `backend/graph/__init__.py` `ruff check .` pass | — |
| 1 | 1 | schema.sql v1 FROZEN | done | `schema.sql` + `backend/graph/schema.sql` symlink — duckdb :memory: verified tables(geo_cache,nodes,edges) indices(5) — grep accuracy_radius hint-only | Next fixture + geo.py |
| 2 | 2 | fixture 500 rows + 12 tests RED | done | `tests/fixtures/m2_small.parquet` 500 rows 12 cols + `scripts/generate_m2_fixture.py` Wasabi≥20 + `tests/test_graph.py` 14 tests (RED → later GREEN) | geo.py |
| 3 | 3+4 | geo.py 243 LOC batch 100K<1s + layers 4 layers Louvain | done | `backend/graph/geo.py` haversine Moscow special + GeoEnricher :memory: 0.005s/100K + `backend/graph/layers.py` + `_coinjoin.py` is_coinjoin triple-gate (W/J/K) | build.py |
| 4 | 5+6 | build.py 249 LOC → duck.db+parquet+DiGraph | done | `backend/graph/build.py` CLI --input/--out/--duckdb -- 3531 nodes/2627 edges 5 indices nodes.parquet 127K edges.parquet 190K | verifier |
| 7 | 7 | verifier GREEN + coord close (Wave5) | done | duck.db 5.8M 3531 nodes 2627 edges geo_cache 0 indices 5 ratio 0.0008<0.05 GROUP BY ok, pytest 14 passed 5.0s, ruff backend/graph 0 errors (full 8 legacy in tests/scripts), ruff format 0, basedpyright backend/graph 0 errors (full 8 legacy), batch 100K 0.005s<1.0s, MUST NOTs clean, ls data/graph duck.db+2 parquet | M2 DONE → hand off M3 |

## M3 — ML Core (ml/*)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 5+6+7 | 38 feats + Hybrid IF+GNN + calibrate/SHAP | todo | — | Start `ml/features.py` 40/40/20 |

## M4 — Viz Alert (AlertTable+Evidence)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 8a | AlertTable + EvidencePanel | todo | — | Start `AlertTable.tsx` columns |
| 1 | 8a | Scaffold Tailwind4+shadcn+TanStack+openapi Alert/Evidence | done | openapi.yaml 14 paths Alert/Evidence validator OK + vite tailwind4 shadcn Badge Table Input Select Card 50 rows mock | mocks |
| 2 | 8a | Mocks 50 alerts + evidence 38 feats | done | frontend/src/mocks/alerts.mock.ts 50 p0.95→0.52 tier hex64 + evidence.mock.ts shap 38 + fixtures.ts re-export — tsc 0 | api |
| 3 | 8a | API client typed fetch fallback | done | frontend/src/api/client.ts apiFetch 8000ms Abort + alerts.ts listAlerts/getEvidence fallback getMock — tsc 0 grep mock 6 | table |
| 4 | 8a | AlertTable TanStack p sort tier filter pagination | done | AlertTable.tsx rank/wallet/txid p2 tier Crit red High orange Med amber Low slate why geo flag time — sort p desc, tier/search filter, pagination 50, row click onSelectAlert — vitest sort/filter/click 5 passed | panel |
| 5 | 8a | EvidencePanel SHAP waterfall + timelines | done | EvidencePanel.tsx BarChart waterfall top10 |shap| + AreaChart amount + geo pills + burst Bar + accuracy_hint badge — getEvidence AbortController — vitest loading/error 4 passed grep graph 0 | theme |
| 6 | 8a | Dark investigator 1280px a11y | done | index.css @custom-variant dark + risk vars + App 1.7fr/1fr max-w 1280 lg:grid — tsc 0 build 827 modules 1.38MB | e2e |
| 7 | 8a | Playwright alert click <500ms + verifiers | done | playwright.config.ts + tests/e2e/alert-click.spec.ts 1 passed 1.9s + vitest 19 passed 159 tests + tsc 0 build 0 + openapi validator OK — M4 DONE | M5 verify |

## M5 — Viz Graph (Cytoscape+GeoMap+Replay)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 8b | GraphView (preset <2K) + GeoMap + Replay | todo | — | Start `GraphView.tsx` canvas preset |
| 1 | 8b | Scaffold frontend foundation (Wave1 Task1) | in_progress | frontend/package.json + vite.config.ts + tsconfig.json + src/App.tsx + stubs — `npm run build` vite 7.3.1 32 modules 656ms exit 0, `tsc --noEmit` exit 0, `vitest --run` 1 passed 618ms | Task2 GraphView preset <2K |

## M6 — Platform+Harness (scripts/*, docker, eval)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 9+10 | Wheels quad + compose <180s + harness σ-sweep | todo | — | Start `scripts/build_wheels.sh` |
| 1 | 9+10 | M6 verifier gate S1+S2+S3 PASS | done | `docker compose config` COMPOSE_OK `uv run TestClient /api/health` HEALTH_OK 200 `tests/test_offline.sh` OFFLINE_OK+CPU_FALLBACK_OK `TORCH_BLAS_PREFER_HIPBLASLT=0 pytest tests/test_rocm_parity.py` 4 passed `pytest tests/test_ingest.py tests/test_graph.py` 40 passed `bench.json` p50 1903ms<2000 `bundle.tar` 2.8G 163 blobs `dist/manifest.json` `data/eval/pr.json` 0.51 `stress.json` 0.615 `sigma_sweep.json` Country/ASN | M6 DONE → Lead |

## Lead — You (integration + docs + locks)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| 0 | 0+10 | Decisions + FINAL + prompts + coord scaffold | done | `PROTOTYPE_DECISIONS_FINAL.md` 30KB | Unblock M1-M6 wave 1 |

| 2 | 8b | E2E Verification 3-scenario contract coverage playwright git-forbidden | done | vitest 172 passed 20 files 53s coverage v8 enabled (npm run test: vitest run --coverage) + playwright 8 specs (tests/e2e/m5.spec.ts + e2e/m5.spec.ts) happy <500ms sigma toggle edge 422/404/offline/0-rows adjacent limit/city/mutation via page.route + vitest fallback 13 tests all green | tsc --noEmit clean build 827 modules 3.64s gzip 419k bench/report.json passed:true fps80 120 fps2000 45 alertToGraph 42 guardrails true | M5 DONE -> handoff M3/M4 |
