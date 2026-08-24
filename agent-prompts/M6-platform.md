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

# M6 — Platform + Harness Agent Prompt (SIH26146 Parts 9+10 assist)

**Owns:** `scripts/build_wheels.sh`, `scripts/bundle.sh`, `scripts/eval/*` (pr.py, stress.py, sigma_sweep.py, bench/*), `Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml` (with Lead), `wheels/`, `data/eval/*`, `docs/assets/*`, `model_card.md` (with Lead), `tests/test_rocm_parity.py`

**Reads:** All `data/*`, `models/*`, `frontend/dist/*`

**GOAL:** Air-gapped Docker <3min cold-start + eval harness (PR-AUC + stress + sigma sweep + fidelity) + bundle manifest. Wrapper-proof gate.

**STACK:** Docker Compose, `pip wheel` quad, `libmaxminddb`, `mbtiles`, bash, Python (sklearn metrics), duckdb CLI.

**MUST DO:**
1. Implement `scripts/build_wheels.sh` quad: `pip wheel --wheel-dir wheels/ -r requirements.cpu.txt` + `pip wheel --wheel-dir wheels/ -r requirements.rocm.txt` with `--platform manylinux2014_x86_64 --python 3.11 --abi cp311 --implementation cp --only-binary=:all:` vs `pip wheel` for build-deps (per FINAL §2 Part9). Include `geoip2`, `polars`, `duckdb`, `torch`. Verify `pip install --no-index --find-links wheels/ -r requirements.cpu.txt` offline.
2. Implement `Dockerfile.api`/`Dockerfile.web` with digest pins (`image: python:3.11-slim@sha256:...`), `COPY wheels/ /wheels && pip install --no-index --find-links /wheels`, `COPY mmdb /app/mmdb`, `HEALTHCHECK CMD curl -f http://localhost:8000/api/health`, `network: internal: true` air-gapped.
3. Implement `docker-compose.yml` (with Lead) 3 services, cold-start <180s; `scripts/bundle.sh` creates `bundle.tar` (`docker save`) + USB layout: `wheels/`, `mmdb/`, `models/`, `data/raw/synthetic/`, `dist/`.
4. Implement `scripts/eval/pr.py` (DFRWS leakage-free 70/30 temporal+graph-disjoint → PR-AUC, ECE), `stress.py` (200 injects → detection@5% FPR), `sigma_sweep.py` (5/30/120 → `sigma_sweep.json`), `bench/*` (ingest <2s, viz >30fps, `rocm_parity` ≤1e-4). Artifacts → `data/eval/*.json + *.png`.
5. Implement `model_card.md` template (bias: CoinJoin FP, geo area hint p90 10×, Africa 66-72% failure, warrant note investigator-assist, limitations, env).
6. Tests: `pytest tests/test_rocm_parity.py` + `bash tests/test_offline.sh` (`curl https://pypi.org --max-time 2 && echo FAIL || echo OFFLINE_OK`).

**MUST NOT DO:** Do NOT own `backend/*`, `ml/*`, `frontend/*` code; do NOT `apt-get` at finale (vendor debs); do NOT use tag `latest` (digest only).

**VERIFY:** On finale-class laptop no wifi: `docker compose up -d && timeout 180 bash -c 'until curl -sf http://localhost:8000/api/health; do sleep 1; done' && echo COLD_START_OK` + `timeout 180 bash -c 'docker load -i bundle.tar && docker compose up'` <180s.

**CONTEXT:** See FINAL §2 Part9-10 + §3 submit checklist 7 steps. CPU fallback default (88-93%) per post-synthesis lock.
