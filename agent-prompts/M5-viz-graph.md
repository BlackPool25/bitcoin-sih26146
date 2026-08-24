> **COORDINATION PROTOCOL — READ BEFORE EVERY TURN — MD MEMORY VIA TERMINALS**
> You run in an isolated agent terminal. Coordination is via MD files on disk, not chat.
> **Every turn you MUST:**
> 1. READ at start: `cat .coord/progress.md; cat .coord/learnings.md; cat .coord/handoffs.md; tail -20 .coord/<YOUR_ID>/journal.md` + `cat DECISIONS.md` relevant section
> 2. WORK one atomic todo (your `Owns` table only — never edit another agent's Owns files; if you need them, append to `handoffs.md` with `BREAKING:`)
> 3. WRITE at end (before exit): append to `.coord/<YOUR_ID>/journal.md` using template below, update `progress.md` row (status + evidence path), append to `learnings.md` if you learned a gotcha with file:line, append to `handoffs.md` if you changed a frozen contract (schema.sql, openapi.yaml, feature cols)
> **Journal template (copy into your journal.md each turn):**
> ```
> ## Turn N — YYYY-MM-DDTHH:MM+05:30 — <one-line goal>
> Done: <files:line>
> Learned: <fact with file:line or URL>
> Evidence: <pytest exit 0 | bench 1.6s | curl 200 — paste artifact path>
> Next: <next todo>
> Blocked: <none or handoff needed>
> ```
> **Files on disk:** `~/projects/sih26146-bitcoin-prototype-decisions/.coord/` — global `progress.md`/`learnings.md`/`handoffs.md` + per-agent `M*/journal.md`. Lead's decisions are in `DECISIONS.md` + `PROTOTYPE_DECISIONS_FINAL.md` (read yours). This protocol is NON-NEGOTIABLE — a turn without journal write is incomplete.

# M5 — Viz Graph + Geo + Replay Prompt (SIH26146 Part 8b)

**Owns:** `frontend/src/components/GraphView.tsx`, `frontend/src/components/GeoMap.tsx`, `frontend/src/components/ReplaySlider.tsx`, `frontend/src/cytoscape/*`, `frontend/src/leaflet/*`

**Reads:** `GET /api/graph/{alert_id}` subgraph, `GET /api/replay?at={ts}`

**GOAL:** Cytoscape.js subgraph (80-200 nodes) preset layout <2K viewport >30fps, Leaflet geo display-only, time replay slider. Sigma escape hatch.

**STACK:** Cytoscape 3.30 + `cose-bilkent`/`cola` presets, Leaflet + OSM mbtiles, Recharts.

**MUST DO:**
1. Implement `GraphView.tsx` cytoscape `preset` layout (deterministic, no animate if nodes>1K), `canvas` renderer, nodes: type `ip`=diamond, `wallet`=ellipse, `txid`=rectangle, sized by `p`/degree, edges by amount/weight, bezier disabled for >500 edges; viewport pagination: render only `?limit=2000` max (server paginates). Escape hatch `GraphViewSigma.tsx` (WebGL) if `?renderer=sigma`.
2. Implement `GeoMap.tsx` Leaflet with country/ASN centroids (not street-level), offline mbtiles fallback or canvas if no tiles; markers colored by tier, popup `accuracy_radius` hint (never filter).
3. Implement `ReplaySlider.tsx` scrubs `timestamp` → fetches `GET /api/replay?at={ts}` + updates GraphView via `cy.json()`.
4. Sync with M4: listen `selectedAlertId` prop → fetch `GET /api/graph/{id}`; own no API shape changes without M4.
5. Tests: `npm run bench:viz` <2K preset >30fps (F4), `playwright test` lasso → not required.

**MUST NOT DO:** Do NOT own alert table (M4); do NOT render full 50K graph (always subgraph); do NOT use city as feature-truth.

**VERIFY:** `npm run bench:viz` → 2K >30fps, 5K stall repro shown; `playwright test` select alert → graph renders <500ms with nodes sized.

**CONTEXT:** See FINAL §2 Part8 + F4 split 76-82% arch vs 55-65% SLA. Never render 50K raw — paginate.
