# Journal — M4-viz-alert — Per-Turn Progress + Learnings

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

## Turn 1 — 2026-08-24T09:35+05:30 — AlertTable + EvidencePanel ranked table p0.95→0.52 + SHAP waterfall
Done: frontend/src/components/AlertTable.tsx:1 TanStack Table rank/wallet/txid p2 tier Badge why geo time sort p desc filter tier/search pagination 50 onSelectAlert; frontend/src/components/EvidencePanel.tsx:1 SHAP BarChart waterfall + Amount AreaChart + geo timeline pills + burst BarChart + accuracy_hint badge; frontend/src/api/client.ts:1 apiFetch AbortController 8000ms fallback; frontend/src/api/alerts.ts:1 listAlerts/getEvidence typed; frontend/src/types/alert.ts:1 38 feats + tierFromP; frontend/src/mocks/alerts.mock.ts + evidence.mock.ts 50 rows mulberry32(42) txid hex64; frontend/src/components/ui/badge|table|input|select|skeleton|card|button; frontend/src/index.css + vite.config.ts tailwindcss vite + dark tokens; openapi.yaml:150 Alert/Evidence schemas + query limit/sort/tier/q/offset; frontend/playwright.config.ts + tests/e2e/alert-click.spec.ts + src/__tests__/alertTable|evidencePanel|apiAlerts + App.tsx wiring 1.7fr/1fr 1280px
Learned: TanStack pagination 50 via getPaginationRowModel + initialState pageSize 50; Recharts vertical BarChart needs ResponsiveContainer width 100% height 320 + layout vertical; @custom-variant dark (&:is(.dark *)) required for Tailwind4 dark class; apiFetch fallback to mock on 404 must check isAbortError before fallback; frontend/vite testTimeout 20000 needed for GraphView cytoscape mount 52s — vite.config.ts:35; openapi placeholder to full schema needs components/schemas Alert/Evidence/Error/ShapMap/GeoPoint + preserve TransactionRecord — openapi.yaml:273
Evidence: tsc --noEmit exit 0; npm run build vite 7.3.1 827 modules 1.38MB gzip 419KB exit 0; vitest 19 passed 159 tests exit 0; playwright alert click 1 passed 1.9s; openapi validator OK 14 paths 10 schemas; grep /api/graph in M4 0; dist/index.html 0.55KB + CSS 42KB
Next: M5 GraphView preset <2K verification + M3 ranked.parquet live backend integration (fallback currently mock)
Blocked: none — M4 DONE, handoff to M5/M6 Lead for 5-min judge walkthrough

