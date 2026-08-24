# Journal — M5-viz-graph — Per-Turn Progress + Learnings

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

## Turn 1 — 2026-08-24T09:09+05:30 — Scaffold frontend foundation (Wave1 Task1)
Done: frontend/package.json:1-44 deps react 19.2.7 cytoscape 3.30.4 etc., frontend/vite.config.ts:1-35 alias @ proxy /api test jsdom, frontend/tsconfig.json:1-22 strict ES2022, frontend/tsconfig.node.json:1-18 composite true, frontend/index.html:1-15 root div, frontend/src/main.tsx:1-14 createRoot StrictMode leaflet.css, frontend/src/App.tsx:1-28 selectedAlertId searchParams renderer cytoscape guard useRef, frontend/src/test-setup.ts:1 jest-dom, frontend/src/components/GraphView.tsx:1-8 stub, GeoMap.tsx:1-9 stub, ReplaySlider.tsx:1-8 stub, frontend/src/cytoscape/{styles,layout,pagination}.ts, frontend/src/leaflet/{tileLayer,markers,fallback}.ts, frontend/src/types/index.ts:1-12 CyJson GeoPoint, frontend/src/mocks/fixtures.ts, frontend/src/bench/index.ts, frontend/src/__tests__/smoke.test.tsx:1-8 App renders placeholder
Learned: @testing-library/react@15 peer react ^18 conflicts with react 19.2.7 — need --legacy-peer-deps; @types/cytoscape-cose-bilkent does not exist on npm 404; tsconfig project references require composite:true not noEmit (TS6306)
Evidence: npm run build exit 0 — vite v7.3.1 built 32 modules dist/assets/index-DlR6S4sq.js 194k gzip 61k 656ms | npx tsc --noEmit exit 0 clean | npx vitest --run --reporter=verbose 1 passed (smoke.test.tsx App renders placeholder) Duration 618ms vitest 2.1.4 | lsp_diagnostics declined/no LSP — tsc as ground truth clean
Next: Task2 — GraphView preset <2K cytoscape canvas + real data wiring
Blocked: none


## Turn 2 — 2026-08-24T10:15+05:30 — Wave6 Task9 E2E Verification Evidence & Handoff final RED->GREEN->SURFACE audit
Done: frontend/src/__tests__/m5.contract.test.tsx 13 tests happy/edge/adjacent, frontend/tests/e2e/m5.spec.ts + frontend/e2e/m5.spec.ts 8 playwright specs happy/edge/adjacent, frontend/package.json test: vitest run --coverage + playwright 1.48.2, frontend/src/bench/fps.test.ts skip __tests__ guard fix, frontend/playwright.config.ts webServer npm run dev reuseExistingServer, vitest 172 passed 20 files 53s, bench/report.json passed true fps80 120 fps2000 45 alertToGraph 42, build 827 modules
Learned: fake-indexeddb auto import required for leaflet offline IndexedDB chain in jsdom otherwise L.map fails via fake-indexeddb/auto — src/test-setup.ts:70; cytoscape headless pixelRatio 1 forced via PIXEL_RATIO guard prevents retina scaling mismatch — src/cytoscape/styles.ts; sigma dynamic import must fallback to mock sentinel in jsdom without WebGL otherwise sigma kill throws — src/components/GraphView.tsx:203; EvidencePanel shap fallback needs 404 not 200 [] else Object.entries(null) crash — src/api/alerts.ts fallback via ApiError 404 triggers getMockEvidence
Evidence: npx vitest run 20 passed 172 passed 53.95s | npx tsc --noEmit exit 0 clean | npm run build vite 7.3.1 827 modules 3.64s gzip 419k | bench/report.json passed:true fps80 120>30 fps2000 45>30 alertToGraphMs 42<500 guardrails pixelRatioOk batchOk haystackOk limitOk true | git diff --stat forbidden check: schema.sql/backend/api/ingest.py no M5 mutation (only pre-existing openapi.yaml M1-M4), app fetch limit=2000 verified | playwright m5.spec.ts 8 scenarios routed via page.route mockFetch (graph limit, replay 422, sigma toggle, invalid 404, offline) + vitest fallback 3 scenarios green | lsp_diagnostics declined/no LSP — tsc as ground truth clean
Next: M5 DONE -> hand off M3/M4, next E2E done, no further M5 work
Blocked: none
