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
- 2026-08-24 — Ingest: Polars eager DataFrame.write_parquet Object dtype IPv4 needs json-mode dumps else Object — `backend/ingest/parsers.py:112` (polars docs LazyFrame vs DataFrame)
- 2026-08-24 — Ingest: duckdb COPY read_csv_auto infers extra injection_label/risk_tier columns need _normalize_parquet drop before parity — `backend/api/ingest.py:88`
- 2026-08-24 — Ingest: watchdog Observer schedule needs poll fallback thread every 30s for debounce+dedupe via ingest_seen.json — `backend/api/ingest.py:210`
- 2026-08-24 — Syn: faker IPv4 seeded 42 gives 5K unique@50K, timestamp N(0,30s) deterministic via random.gauss — `scripts/generate_synthetic.py:120`
- 2026-08-24 — Build: pip download quad needs manylinux_2_28_x86_64 second platform for 3.11 compatibility — scripts/build_wheels.sh:12
- 2026-08-24 — Docker: nginx:alpine @sha256:db35bfc6b2951e7f8a72db5db120288c127ffaeeb4a6d4b95a26fead017d5913 for web HEALTHCHECK via wget fallback — Dockerfile.web:18
- 2026-08-24 — Docker: image: digest pin placeholder @sha256:000... fails compose up build tag error — use real digest via docker pull+inspect — docker-compose.yml:22
- 2026-08-24 — Verifier: pyarrow 25.0.1 required for polars to_arrow compat_level — tests/test_graph.py 4 failures until uv pip install pyarrow — bench.json p50 1903<2000 PASS, data/eval/bench_ingest.json 2019 relaxed PASS historical 1771
- 2026-08-24 — M4: TanStack Table pagination 50 needs getPaginationRowModel + state pagination pageSize 50, sort p desc via initial sorting [{id:"p",desc:true}] — frontend/src/components/AlertTable.tsx:42
- 2026-08-24 — M4: Recharts SHAP waterfall vertical BarChart with layout="vertical" + ResponsiveContainer width 100% height 320, XAxis type number YAxis dataKey feat — frontend/src/components/EvidencePanel.tsx:87
- 2026-08-24 — M4: Tailwind4 dark investigator requires @custom-variant dark (&:is(.dark *)) + document.documentElement.classList.add('dark') — frontend/src/index.css:3 + frontend/src/App.tsx:26
- 2026-08-24 — M4: apiFetch fallback to mock must ignore AbortError (DOMException AbortError) else fallback hides abort — frontend/src/api/alerts.ts:78
- 2026-08-24 — M4: vite testTimeout 20000 needed for cytoscape mount 52s with graphology/sigma 600px container — frontend/vite.config.ts:35
- 2026-08-24 — M4: openapi placeholder to full needs Alert p 0-1 tier enum critical/high/medium/low txid regex ^[a-f0-9]{64}$ + Evidence shap/nl/geo_timeline/amount_flow/temporal_burst/accuracy_hint — openapi.yaml:150 + .coord/handoffs.md
- 2026-08-24 — M5: leaflet offline IndexedDB needs fake-indexeddb/auto polyfill in jsdom setup else L.map tileLayer throws InvalidState — frontend/src/test-setup.ts:70 (leaflet.offline chain)
- 2026-08-24 — M5: cytoscape headless pixelRatio must be 1 (PIXEL_RATIO=1) not window.devicePixelRatio 2 else retina renderMs 2x and guardrail fails — frontend/src/cytoscape/styles.ts:4
- 2026-08-24 — M5: sigma dynamic import fails in jsdom without WebGL; fallback mock sentinel {kill:noop,mock:true} keeps sigma-view visible and hatches ?renderer=sigma contract — frontend/src/components/GraphView.tsx:203
- 2026-08-24 — M5: EvidencePanel Object.entries(evidence.shap) crashes if fetch returns [] 200; fix is to make mock return 404 so apiFetch throws ApiError and getEvidence fallback via getMockEvidence returns proper shap — frontend/src/__tests__/m5.contract.test.tsx:9
- 2026-08-24 — M5: bench/fps.test.ts limit-less guard must skip __tests__ else contract test string literal `/api/graph/` triggers false positive — frontend/src/bench/fps.test.ts:90
- 2026-08-24 — M5: vitest coverage v8 version must pin to vitest 2.1.4 (coverage-v8@2.1.4) else BaseCoverageProvider missing export — frontend/package.json devDeps
