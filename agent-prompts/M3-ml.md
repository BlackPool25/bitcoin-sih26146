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

# M3 — ML Core Agent Prompt (SIH26146 Parts 5+6+7)

**Owns:** `ml/features.py`, `ml/train.py`, `ml/train_gnn.py`, `ml/ensemble.py`, `ml/calibrate.py`, `ml/explain.py`, `data/features/features.parquet`, `models/if.pkl` + `gnn.pt` + `calibrator.pkl`, `data/alerts/ranked.parquet` + `explanations.json`, `requirements.rocm.txt` + `requirements.cpu.txt`

**Reads:** `data/graph/nodes.parquet`, `edges.parquet`, `duck.db` (M2)

**GOAL:** 38 feats 40/40/20 → Hybrid IF(0.4)+GNN(0.6) → Platt+isotonic calibrated p → SHAP NL. CPU fallback mandatory.

**STACK:** Polars, NetworkX metrics, sklearn (IF, LOF, XGB, calibration, isotonic), torch + torch_geometric (GCN/GAT), shap, ROCm 7.14 gfx1100 (TheRock), Looong01 pyg-rocm-build.

**MUST DO:**
1. Implement `ml/features.py` 15+15+8=38 feats (see FINAL §2 Part5) → `data/features/features.parquet` SHAP-ready; avoid leaked 72 agg from Elliptic 166.
2. Implement `ml/train.py` IF: `IsolationForest(contamination=0.02, n_estimators=200)` + LOF, train <5s, save `models/if.pkl`; also XGB `XGBClassifier` for ablation (XGBCLUS under-sampling per SciDirect).
3. Implement `ml/train_gnn.py` load pre-trained GNN (not train at finale): `GCNConv(38→64→32)+Linear(32→2)` weights from `models/gnn.pt` (trained offline on 7900GRE with `TORCH_BLAS_PREFER_HIPBLASLT=0` on gfx1100). Bundle both cpu+rocm wheels. `requirements.rocm.txt`: `torch[device-gfx1100]` via repo.amd.com + Looong01 wheels for `torch_scatter/sparse/cluster/spline`; `requirements.cpu.txt`: `torch --index-url https://download.pytorch.org/whl/cpu`.
4. Implement `ml/ensemble.py` `p_raw = 0.4*sigmoid(IF)+0.6*softmax(GNN)[1]` with hedge: if DFRWS builder Δ<0.05, flip to XGB-only and report ablation.
5. Implement `ml/calibrate.py` Platt sigmoid + Isotonic challenger on 30% hold-out, ECE<0.05, tiers Crit>0.90 / High 0.75-0.90 / Med 0.50-0.75 / Low.
6. Implement `ml/explain.py` TreeSHAP inline 5-30ms for IF/XGB + Jinja NL, GNNExplainer+attention async 200-5000ms (Redis cache), do NOT SHAP leaked 166. Save `data/alerts/ranked.parquet` + `explanations.json`.

**MUST NOT DO:** Do NOT train GNN at finale (load weights), do NOT SHAP leaked aggregates, do NOT claim hybrid beats by 5pp unless builder Δ≥0.05, do NOT break CPU fallback.

**VERIFY:** `pytest tests/test_ml.py -k "if_train <5s"` + `python ml/infer.py --graph data/graph/ --out data/alerts/ranked.parquet` + `pytest test_rocm_parity --device cpu` + `pytest test_rank -k "tiers monotonic"` + `rocminfo` parity ≤1e-4 on your 7900GRE before Sep freeze.

**CONTEXT:** See FINAL §2 Part5-7 + §1 locks (hybrid residual, CPU fallback 88-93%, σ-sweep hedge).
