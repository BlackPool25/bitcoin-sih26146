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
| 0 | 0 | Bootstrap git+pyproject+dirs+coord (Wave0) | in_progress | `pyproject.toml:geoip2` `backend/graph/__init__.py` `ruff check .` pass | Next T1 `backend/graph/schema.sql` |

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

