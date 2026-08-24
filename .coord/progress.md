# Progress Board — SIH26146 (global, append-only per-agent sections)

> Each agent appends one row per turn under their header. Status: todo | in_progress | done | blocked. Keep ONE in_progress per agent.

## M1 — Ingest (backend/ingest/*)
| Turn | Part | Task | Status | Evidence | Next |
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

## M5 — Viz Graph (Cytoscape+GeoMap+Replay)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 8b | GraphView (preset <2K) + GeoMap + Replay | todo | — | Start `GraphView.tsx` canvas preset |

## M6 — Platform+Harness (scripts/*, docker, eval)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| — | 9+10 | Wheels quad + compose <180s + harness σ-sweep | todo | — | Start `scripts/build_wheels.sh` |

## Lead — You (integration + docs + locks)
| Turn | Part | Task | Status | Evidence | Next |
|------|------|------|--------|----------|------|
| 0 | 0+10 | Decisions + FINAL + prompts + coord scaffold | done | `PROTOTYPE_DECISIONS_FINAL.md` 30KB | Unblock M1-M6 wave 1 |

