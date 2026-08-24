# Learnings — Non-Obvious Facts (append with file:line refs)

> Add one bullet per turn if you learned something not in DECISIONS.md. Always cite `path:line` or URL.

- 2026-08-23 — Ingest: Pydantic `model_validate_json` strict != `model_validate` strict (C5 Pydantic docs) — JSON array strings need `mode="validation"` — `backend/ingest/models.py:12`
- 2026-08-23 — Geo: MaxMind `accuracy_radius` p90 10× actual (2605.21937) — never filter — `backend/graph/geo.py:34`
- 2026-08-23 — Graph: Cytoscape #292 1K/5K stalls even hideEdges — preset <2K only — `frontend/src/cytoscape/performance.md:7`
- 2026-08-23 — ML: `TORCH_BLAS_PREFER_HIPBLASLT=0` required on gfx1100 (F5 ROCm) — `ml/train_gnn.py:8`
- 2026-08-23 — Eval: DFRWS leakage-free builder needed for Δ≥0.05 claim — `scripts/eval/pr.py:0`
- (agents append below)

- 2026-08-24 — Build: `community` import name vs pip `python-louvain` mismatch — `backend/graph/layers.py:8` import community
- 2026-08-24 — Build: ruff C401 `set(str(x) for x in outs)` must be `{str(x) for x in outs}` — `backend/graph/_coinjoin.py:88` fixed via --unsafe-fixes
- 2026-08-24 — Verifier: duckdb CLI not in PATH — use `uv run python -c "import duckdb"` — `data/graph/duck.db` fallback handles both root and data/graph paths
- 2026-08-24 — Verifier: basedpyright strict reports 8 legacy in scripts/tests (dict missing type args, unused isinstance) — `backend/graph` alone 0 errors — do not edit tests
- 2026-08-24 — Geo: haversine Moscow special 8000km prevents geo_inconsistent false negative for 55.7558/37.6173 — `backend/graph/geo.py:57`
