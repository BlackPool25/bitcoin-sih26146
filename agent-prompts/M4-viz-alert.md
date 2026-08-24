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

# M4 — Viz Alert Table + Evidence Panel Prompt (SIH26146 Part 8a)

**Owns:** `frontend/src/components/AlertTable.tsx`, `frontend/src/components/EvidencePanel.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/alerts.ts`

**Reads:** `GET /api/alerts`, `GET /api/evidence/{id}` (from M3 ranked.parquet)

**GOAL:** Alert-first landing: ranked table (p 0.95→0.52) → click → evidence panel (geo timeline, amount flow, SHAP waterfall). Wrapper-proof polish.

**STACK:** React 19 + Vite 6 + TypeScript + shadcn + TanStack Table + Recharts + Tailwind.

**MUST DO:**
1. Implement `AlertTable.tsx` columns: rank, wallet/txid (truncated), p (2 decimals), tier badge (Crit/High/Med/Low color), why (top SHAP feature), geo (country flags), time; sort by p desc, filter by tier/search; pagination 50; row click → `onSelectAlert(id)`.
2. Implement `EvidencePanel.tsx` on select: fetch `GET /api/evidence/{id}` → show `explanations.json` fields: SHAP waterfall (Recharts bar), amount Sankey/timeline, geo timeline (country path), temporal burst chart; `isaccuracy_hint` badge for radius.
3. Implement `frontend/src/api/*` typed client (openapi generated), handle loading/error; own API shape proposal — PR to `openapi.yaml` v1.
4. Style shadcn: dark investigator theme, risk colors (Crit red, High orange, Med amber, Low slate), responsive 1280px, a11y.
5. Tests: `playwright test` click first alert → EvidencePanel renders <500ms.

**MUST NOT DO:** Do NOT own `GraphView.tsx`, `GeoMap.tsx`, `ReplaySlider.tsx` (M5); do NOT fetch graph subgraph (M5 does); do NOT write backend.

**VERIFY:** `npm run dev` → `http://localhost:5173` ranked table loads <1s, `npm run build` passes, `npx playwright test --grep "alert click"` PASS.

**CONTEXT:** See FINAL §2 Part8. API freeze — M4 proposes shape, M5 reads after.
