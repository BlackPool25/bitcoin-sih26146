# PROTOTYPE DECISIONS FINAL — SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic (NTRO)

**Date:** 2026-08-23 — Post-Synthesis (Ultra-Research Complete 74-87% / 42-68% contested)  
**Research Dir:** `/home/shreyas/Downloads/OmniLearn/.omnilearn/research/sih26146-bitcoin-transaction-traffic/` — 52 sources, 16 queries, 8 contradictions → 5 hypotheses → 41 searches → 5 contested findings  
**Pre-synthesis decisions:** `DECISIONS.md` (392 lines, 28 Q&As) — this file LOCKS the 7 pendings with numeric confidence + adds verifier commands, bundle manifest, and per-part agent prompts.  
**Team:** 6-member SIH, Sep 20 deadline 20 Sep 2026 0/500, WIN intent (wrapper-intolerant NTRO), Python+FastAPI+React, AMD 7900GRE gfx1100, air-gapped Docker <3min, 50K/80K/5K slider, agent-buildable partition (you = lead integrator).  
**Status:** `05-iterations/iteration-001.md` + `findings.md` F1-F5 + `conclusions.md` + `recommendations.md` all verified 2026-08-23.

> **How to use:** Hand one row of §3 to one agent. No agent edits another's `Owns` paths. API shape and `duck.db` schema are FROZEN — PRs that break them are rejected. Verifiers in §4 must PASS before `git push`.

---

## §0 Locked PS Spec (Cite-Verified, No Invention)

**PS:** SIH26146 | Title: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic | Org: NTRO | Theme: Transportation & Logistics (csv label; domain is Blockchain & Cyber) | Category: Software | `dataset_link=""` empty verified `csv.DictReader` 2026-08-21 | `youtube_link=""` | 0/500 | Rank 1/75 PASS FRESH (tie SIH26163) | Viability 8.2/10 PICK NOW.

**Objectives (5):** (1) Ingest CSV/JSON/XML (`timestamp, src_ip, dst_ip, src_port, dst_port, txid, input_addresses[], output_addresses[], input_amounts[], output_amounts[], fee, script_type`) (2) Entity/transaction graph IPs↔wallets↔TXIDs (3) Working ML not just rules (Section-4 table unknown beyond excerpt) (4) Ranked explainable alert list (why+confidence) (5) Simple dashboard or link-analysis viz.  
**Dataset:** Synthetic modelled on real P2P/transaction fields + `geo_country/asn` via MaxMind GeoLite2 downloadable DB.  
**Expected:** Offline Linux prototype + write-up (approach, model choice, explainability) + dashboard with evidence per flag.  
**Scoring:** base 50 + org 10 (NTRO HIGH 70-80% — 13 winners 2024 at `sih.gov.in/sih2024/sih2024-grand-finale-result` + MIC Report p3-4) + data 1 (empty but Elliptic/GeoLite/APIs) + demo 6 (28-32h path) + team 6 + novelty 2 (Blockchain 3.5% rare) −0 competition (Transportation 7/155 4.5%).  
**Freshness:** FRESH 79/155 (51%), near-match only SIH260378 J=0.125 1 token (<45 threshold fail), GitHub SIH26146 0.

---

## §1 Architecture Decisions (Post-Synthesis Locked)

| Pending Pre-Synthesis | Synthesis Finding & Confidence | Final Decision (LOCKED) | Fallback if Falsified |
|---|---|---|---|
| Polars vs DuckDB ingest | F4: Hybrid sink 76-82% arch established (DuckDB 12ms query outlier vs Polars 8.7s, but **sink 3.5 vs 3.9s parity 1.1×** → hybrid Arrow zero-copy consensus). SLA 55-65% contested (workload <2s depends on technique). | **Hybrid: Polars `sink_parquet` (streaming) → DuckDB `COPY`/`read_parquet`**. Ingest via Polars streaming (`sink_parquet` Arrow), persist via DuckDB Parquet copy, query via DuckDB. Verifier: `python -m pytest ingest_bench` <2s on 50K. | Pure DuckDB `read_csv_auto` + `COPY (HEADER TRUE)` if Polars Pydantic overhead stalls >5s — keep both code paths behind feature flag `INGEST_ENGINE=polars|duckdb`. |
| Cytoscape vs Sigma/vis-network at 50K | F4: Cytoscape 1K/5K overloaded even `hideEdges` (issue #292 zoom slow) 72% established; Sigma WebGL conditional (5K/100K only if not updating) L4 60% ; <2K preset >30fps established. | **Cytoscape `cose-bilkent` preset + viewport pagination <2K (server-side NetworkX prep, client renders filtered shard). Sigma as escape hatch if viewport >2K needed.** Verifier: `npm run bench:viz` <2K >30fps, 5K stalls repro. | Split workload: full 50K stays in DuckDB+NetworkX; cytoscape renders `GET /api/graph/{alert_id}` subgraph (≈80-200 nodes) not full graph — never render 50K raw. |
| Hybrid ≥5pp PR-AUC over XGB leakage-free? | F1: 42-58% contested — ChronoWave 0.98 transductive vs Bhavesh repro **XGB 0.669 >> GCN 0.198 / GAT 0.184 (49% gap)** + DFRWS >90% semantics @575059 leakage. | **Hybrid as RESIDUAL not headline** — Report **XGB 0.669** as primary SOTA (leakage-aware), hybrid 0.4/0.6 as ensemble lift *only if DFRWS leakage-free builder Δ≥0.05*. Lead story: "tabular wins leakage-free; hybrid adds robustness". | Lead with XGB + XGBCLUS + SHAP; GNN is secondary lane with `GNNExplainer` + attention, not main metric. |
| CoinJoin-gated Louvain cuts FPR ≥30%? | F2: 48-62% contested — Kappos RF 89.2% vs rule 87.5% FNR 10%→20% halved + Louvain 2M/2min (supporting), but JoinMarket 0.4-0.7 conf floor + r≈0.5 @700k + one-time change blind 33% + Pairwise 0.83 masks contamination (contradicting). | **Gated Louvain as 3-way ablation, not promised 30% cut** — Runs: (a) CIOH raw, (b) CIOH+CoinJoin filter, (c) +Louvain communities → report FPR delta; promise "gate prevents superclusters" not numeric 30%. | Document JoinDetect era drift, Wasabi 2.0+ ≥20 inputs change, OTC blind — show ablation table even if Δ<30%. |
| Network jitter σ=30s + GeoLite geo adds ≥3pp? | F3: 38-55% contested — Zheng 81.3% lab (+30% SOTA) but diffusion/Dandelion++ 90/10 stem 10 hops embargo + supernode leak >30% 300ms/hop; GeoLite City ≤5km 25-35% (cellular 5.7%) mobile median 204km p90 10×, 66-72% Africa failure; BDC 25.7% NA ≤5km. | **Country/ASN as feature (not city truth), city display-only; run σ-sweep 5/30/120ms → hedge as Country/ASN if Δ≤0.03.** Verifier: σ=30s PR-AUC Δ ≥0.03 to keep jitter; else drop city. | Accuracy_radius HINT not filter (`isaccuracy_hint`); 51% exceed radius — document "area, not point". |
| SHAP vs GNNExplainer | F3 opacity: SHAP on 166 leaked aggregates misleads (DFRWS), GNN needs `GNNExplainer`+attention (IJCNC 2025). Production pattern: TreeSHAP 5-30ms inline, Kernel async 200-5000ms (L5). | **Split: TreeSHAP (IF/XGB) inline 5-30ms + SHAP NL template; GNN lane uses GNNExplainer+attention subgraph masks (IJCNC), async Redis cache. Do NOT SHAP 166 leaked feats.** | If GNNExplainer slow, fall back to attention weights + top-3 GNN node features only. |
| Synthetic fidelity (FinDiff 0.954) | WITS 2024: FinDiff column 0.954/row 0.985 best fidelity, DGAN best privacy, AMLworld agent-based for typology control, NetSimile 30-31 poor discrimination. | **AMLworld typology (agent-based) for 50K/80K/5K injection (peel/mixer/CoinJoin), WITS KS/NetSimile/DCR report for validation, FinDiff if bank-style fidelity needed.** Report KS + DCR + NetSimile (even if ~30) — judges want fidelity sheet, not raw scale. | If time short, pure faker+random with seeded RNG still valid per spec — AMLworld is enhancement not gate. |
| ROCm PyG on gfx1100 viability | F5: 18-28% full stack (ROCm #3655 not on roadmap, thrust→hipthrust miss, glibc 2.32+, HIPBLASLT unsupported gfx1100), 52-64% MessagePassing-only (hipSPARSE BSR parity ≤1e-4), 88-93% CPU fallback guarantee. | **ROCm 7.14 `torch[device-gfx1100]` first-class OK, PyG = MessagePassing-only via `Looong01/pyg-rocm-build` (hipSPARSE) + CPU fallback MANDATORY. Train offline on AMD, demo CPU.** Verifier: `TORCH_BLAS_PREFER_HIPBLASLT=0` on gfx1100 + `pytest rocm_parity` ≤1e-4 fp32 + TheRock shard <2× CUDA. | CPU-only finale if wheels fail: `pip install torch_geometric` CPU + `pyg_lib` cpu/cu121 fallback — always bundle both wheels. |

---

## §2 Full Stack per Part (File Paths + Stack + Commands + Config)

### Part 1 — Ingestion & Normalization Pipeline — Owner: M1 Backend Ingest
**Goal:** Ingest bulk CSV/JSON/XML → validated Parquet + validation report.  
**Owns:** `backend/ingest/models.py`, `backend/ingest/parsers.py` (polars/ijson/lxml), `backend/api/ingest.py` (FastAPI `POST /api/ingest`), `data/clean/parquet/*.parquet`, `data/reports/validation.json` — **no one else writes these.**  
**Models:** Pydantic v2 `TransactionRecord` (fields: `timestamp datetime`, `src_ip IPv4`, `dst_ip IPv4`, `src_port int 0-65535`, `dst_port int`, `txid str regex [a-f0-9]{64}`, `input_addresses List[str]`, `output_addresses List[str]`, `input_amounts List[float]`, `output_amounts List[float]`, `fee float`, `script_type Literal["P2PKH","P2SH","P2WPKH","P2WSH","unknown"]`, `geo_country str`, `geo_asn int`) — `strict=True` + `Field(strict=True)` on numeric; `model_validate_json` vs `model_validate` divergence noted (C5).  
**Parsers:** Polars `scan_csv` + `sink_parquet` streaming (100K chunks), `ijson` streaming for JSON, `lxml iterparse` for XML, auto-detect via `magic` + `content-type`; quarantine error rows → `data/reports/validation.json` with `{file, row, error, raw}`.  
**Ingest engines (feature-flag):** `INGEST_ENGINE=polars` → `pl.scan_csv(...).sink_parquet("data/clean/parquet/{file}.parquet")` ; `INGEST_ENGINE=duckdb` → `duckdb.sql("COPY (SELECT * FROM read_csv_auto('data/raw/{file}.csv', HEADER TRUE)) TO 'data/clean/parquet/{file}.parquet' (FORMAT PARQUET)")`.  
**Batch+poll+WS+replay:** FastAPI `POST /api/ingest` (batch upload), folder-watch `watchdog` polling 30s → auto-ingest, WS mock `mempool.space` shape `GET /api/mock/mempool` + `wss://mock/mempool` via `fastapi.websockets`, replay slider `GET /api/replay?at={ts}`.  
**Verifier:** `python -m pytest tests/test_ingest.py -k "50k <2s"` + `make ingest-bench` on 50K CSV/JSON/XML fixture; `curl -F file=@50k.csv http://localhost:8000/api/ingest` → 200 + `validation.json`. Offline: no network call.

### Part 2 — Synthetic Dataset Generator (Elliptic-Anchored 50K/80K/5K) — Owner: M1+M2
**Goal:** 50K txs / 80K edges / 5K IPs with injected illicit patterns, anchored on real Elliptic chain layer + synthetic P2P layer.  
**Owns:** `scripts/generate_synthetic.py`, `data/raw/synthetic/*.csv/json/xml`, `data/eval/fixtures/*` — seeds RNG 42.  
**Anchoring:** Load Elliptic 203,769 nodes / 234,355 edges / 49 timesteps / 166 feats (94 local+72 agg) + 46,564 labels (licit/illicit) via `torch_geometric.datasets.Elliptic` or Parquet export; sample 50K chain layer preserving illicit ratio (~2% → 1000 illicit).  
**P2P layer:** `faker` IPv4 (5K unique), `random.randint(8333, 18333)` ports, `timestamp = tx_broadcast ± N(0,30s)` per peer (Gaussian jitter σ=30s, configurable 5/30/120 for σ-sweep), `geo_country/asn` via GeoLite2 lookup (enricher reuses Part 3).  
**Patterns injected (ranked Crit→Low):** peel chain (1-in-2-out seq, seed BlockSci-style rounds, 624K chains ref), mixing fan-in/fan-out (2-gen mixers, BlockSys 2026 filter), CoinJoin (Wasabi 2.x ≥20 inputs, JoinMarket), structuring (<1 BTC outputs), ransomware burst (8-min fan-out), bridge layering (RSK), high-fee laundering, ASN hopping (RU→CN→US). Each record gets `injection_label` (peel/mixer/coinjoin/...) + `risk_tier`.  
**Exports:** `--format csv|json|xml --scale 1k|10k|50k --sigma 30` → `data/raw/synthetic/synth_50k_{fmt}.csv` + `synth_50k_{fmt}.json` + `.xml`; slider param for judge `GET /api/synthetic?scale=50k&sigma=30`.  
**Verifier:** `python scripts/generate_synthetic.py --scale 50k --sigma 30 && python -m pytest tests/test_synthetic.py -k "fidelity"` → checks KS/NetSimile/DCR + injection_label counts + `head -5` valid txid regex.

### Part 3 — GeoIP/ASN Enrichment Engine — Owner: M2 Graph+Geo
**Goal:** IP → country/city/ASN/lat/lng + `geo_inconsistent` flag, as feature not truth.  
**Owns:** `backend/graph/geo.py`, `data/geo/GeoLite2-City.mmdb`, `data/geo/GeoLite2-Country.mmdb`, `data/geo/GeoLite2-ASN.mmdb`, DuckDB `geo_cache` table.  
**Stack:** `geoip2` + `libmaxminddb` (C) + `maxminddb`, `geoipupdate 4.x` (Docker `maxmindinc/geoipupdate` or R2 presigned `mm-prod-geoip-databases...r2.cloudflarestorage.com`). MMDB unpacked 50-55MB (City) / 6.6-7.6MB (Country) — fits 68MB budget (239-265MB is CSV ZIP, not MMDB).  
**Logic:** `reader.get(ip)` → `{countryIso, city, lat, lng, asn, accuracy_radius}` → cache in DuckDB `geo_cache(ip, country, asn, lat, lng, radius, fetched_at)`; `geo_inconsistent = (country mismatches ASN A record region) OR (dist > 1000km between consecutive txs for same wallet)` — feature only. `accuracy_radius` as HINT, never filter (51% exceed, p90 10× per 2605.21937).  
**Integration:** CSV bulk enrichment via `COPY` join or Polars `map_elements` with batch lookup (100K lookups <1s). Snowball: also vendor `libmaxminddb`, handle R2 allow-list at build (online), pin snapshot date, attribution per EULA (delete within 30d of new release — bundle date-tagged).  
**Verifier:** `python -m pytest tests/test_geo.py -k "100k <1s"` + spot check RU/CN/US IPs map sane; `curl http://localhost:8000/api/geo/8.8.8.8` → `{"country":"US","asn":15169}` (Google) offline after bundle.

### Part 4 — Entity-Transaction Graph Engine (Multi-Layer, Thin Angle) — Owner: M2 Graph+Geo
**Goal:** 4 layers → Louvain communities → graph metrics.  
**Owns:** `backend/graph/build.py`, `backend/graph/layers.py`, `data/graph/nodes.parquet`, `edges.parquet`, `duck.db`, `schema.sql`.  
**Layers:** (1) Network: `IP ↔ TXID` via co-occurrence (same `txid` observed by ≥2 IPs within `|Δt| < 60s + ASN match), (2) UTXO: `wallet ↔ TXID` via `input_addresses/output_addresses` (UTXO graph), (3) Temporal: edge weight decay `exp(-|Δt|/300s)` + burst nodes, (4) Community: Louvain on co-spend graph (`python-louvain` / `community`) on `edges` filtered by CoinJoin.  
**CoinJoin gating (anti-collapse):** Before union-find CIOH (`networkx.utils.union_find`) → gate merges through `is_coinjoin(tx)` filter: Wasabi 2.x heuristic (≥20 inputs, equal output amounts) + JoinMarket fingerprint (0.4-0.7 conf per Schnoering 760k) + Kappos RF fallback — quarantined `coinjoins` don't merge. Peel-chain-aware Louvain: temporal slicing per 10-min window.  
**Storage:** DuckDB `duck.db` with `nodes(id PK, type ENUM('ip','wallet','txid'), country, asn, community_id)` + `edges(src, dst, type ENUM('p2p','utxo','temporal'), amount, ts, weight)` + indices on `src/dst/ts`. NetworkX `DiGraph` for betweenness/PageRank (in-memory 50K fine, spill to DuckDB if >100K). Neo4j rejected (+400MB).  
**Schema freeze:** `schema.sql` v1 locked — others PR to you for `ALTER`.  
**Verifier:** `python backend/graph/build.py --input data/clean/parquet/* --out data/graph/ && duckdb duck.db "SELECT count(*) FROM nodes; SELECT community_id, count(*) FROM nodes GROUP BY 1 LIMIT 5"` → no supercluster (largest community <5% nodes, otherwise collapse bug) + `pytest test_graph -k "coinjoin not merged"`.

### Part 5 — Feature Engineering (40/40/20) — Owner: M3 ML Core
**Goal:** 38 feats SHAP-ready Parquet.  
**Owns:** `ml/features.py`, `data/features/features.parquet`.  
**Network 40% (15):** `unique_peers`, `asn_entropy`, `port_entropy`, `geo_distance_variance_km`, `inv_jitter_std`, `peer_degree`, `asn_hopping_rate`, `port_anomaly_score`, `country_diversity`, `p2p_burst_count`, `rtt_proxy_ms`, `uptime_hours`, ` tor_flag`, `accuracy_radius_mean` (hint), `ws_reconnects`.  
**Chain 40% (15):** `fan_in`, `fan_out`, `output_amount_variance`, `fee_sat_per_vb`, `script_type_hist_P2WPKH_ratio`, `input_count`, `output_dispersion_gini`, `utxo_age_blocks`, `peel_depth`, `mixer_score`, `coinjoin_prob`, `change_addr_likelihood`, `dust_outputs`, `op_return_flag`, `value_median`.  
**Temporal 20% (8):** `burst_5m_count`, `burst_1h_count`, `inter_tx_interval_std`, `modularity_delta`, `hour_entropy`, `day_of_week_entropy`, `community_size`, `betweenness_z`.  
**Stack:** Polars + networkx metrics → `features.parquet`; SHAP-ready (94 local from Elliptic 166 not leaked agg 72 per DFRWS).  
**Verifier:** `python ml/features.py --graph data/graph/ --out data/features/ && python -m pytest tests/test_features.py -k "shape 50k×38"` + `shap.TreeExplainer` dummy run <100ms.

### Part 6 — AI/ML Detection Engine (Hybrid IF+GNN) — Owner: M3 ML Core
**Goal:** Trained IF+LOF (seconds) + loaded GNN (no train at finale) → raw score.  
**Owns:** `ml/train.py`, `ml/model_if.pkl`, `models/gnn.pt`, `ml/ensemble.py`, `requirements.rocm.txt`, `requirements.cpu.txt`.  
**IF+LOF:** `sklearn.ensemble.IsolationForest(contamination=0.02, n_estimators=200)` + `LocalOutlierFactor` on 38 feats → `decision_function` ∈[-∞,∞] per tx/wallet. Train <5s on 50K.  
**GNN:** `torch_geometric` GCN/GAT/GIN on Elliptic: load pre-trained weights (trained offline on AMD 7900GRE gfx1100 via ROCm 7.14) — inference only at demo. Architecture: 2-layer `GCNConv(38→64→32) + Linear(32→2)` or `GATConv` variant; weights from `linovives/bitcoin-fraud-gnn` or own train (`python ml/train_gnn.py --epochs 200 --device cuda` works because `torch.cuda.is_available()` returns True on HIP). Training command (online): `TORCH_BLAS_PREFER_HIPBLASLT=0 python ml/train_gnn.py --device cuda --arch gfx1100` (HIPBLASLT unsupported gfx1100 per F5). Bundle `gnn.pt` (~50MB).  
**Fusion:** `p_raw = 0.4 * sigmoid(IF_score) + 0.6 * softmax(GNN_logits)[1]` — hedge: if DFRWS builder shows hybrid Δ<0.05, flip to `p_raw = XGB_score` and report hybrid as ablation.  
**ROCm HIP (gfx1100):** `pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ torch[device-gfx1100] torchvision torchaudio` + `pip install pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv` from `https://data.pyg.org/whl/torch-{TORCH}+cpu.html` **NOT** ROCm path → use `Looong01/pyg-rocm-build` wheels (`pip install --index-url https://github.com/Looong01/pyg-rocm-build/releases`), glibc ≥2.32, `hipSPARSE` BSR parity ≤1e-4 fp32 (F5 52-64% MP-only). **CPU fallback mandatory** (`requirements.cpu.txt` with `torch+cpu` + `pyg cpu` wheels) — always bundle both. TheRock `rocm[libraries,devel]` ~50MB shards via fat wheel.  
**Verifier:** `pytest tests/test_ml.py -k "if_train <5s"` + `python ml/infer.py --graph data/graph/ --model models/gnn.pt --out data/alerts/raw.parquet` + `pytest tests/test_rocm_parity.py -k "HIPBLASLT 0 <=1e-4"` (run on AMD box before Sep freeze).

### Part 7 — Ranking, Confidence & Explainability — Owner: M3 ML Core
**Goal:** Calibrated p → tiers → SHAP + NL.  
**Owns:** `ml/calibrate.py`, `models/calibrator.pkl`, `ml/explain.py`, `data/alerts/ranked.parquet`, `data/alerts/explanations.json`.  
**Calibration:** Hold-out 30% Elliptic illicit labels → `sklearn.calibration.CalibratedClassifierCV(cv="prefit", method="sigmoid")` (Platt) + `IsotonicRegression` challenger — fit on validation `p_raw vs y`. Verifier: calibration curve `reliability_diagram` ECE <0.05.  
**Tiers:** `Critical >0.90 / High 0.75-0.90 / Medium 0.50-0.75 / Low <0.50` + `confidence = p_calibrated`.  
**Explain:** `shap.TreeExplainer(IF/XGB)` on 38 feats → top-3 `|shap|` → Jinja NL: `"Wallet {addr} flagged: {fan_out} outputs <1 BTC in {burst} min, peers {countries} ASN {asn_hopping} — conf {p:.2f} ({feat1}+{feat2}+{feat3})"`. GNN lane: `torch_geometric.explain.GNNExplainer` subgraph masks + attention weights → `explanations.json: {alert_id, subgraph:{nodes,edges}, shap:{feat: val}, nl}`. Async Kernel SHAP via `shap.KernelExplainer` + Redis cache — TreeSHAP inline 5-30ms, Kernel 200-5000ms (F5) — monitor via `shap-monitor`. Do NOT SHAP the 166 leaked Elliptic aggregates (opaque per DFRWS).  
**Verifier:** `python ml/explain.py --alert data/alerts/ranked.parquet:0 --out - | jq .shap` → 3 feats + `pytest test_rank -k " tiers monotonic"`.

### Part 8 — Visualization & Investigator Dashboard (Alert-First, UX Very Important) — Owner: M4+M5
**Goal:** 5-min judge walkthrough: ranked table → subgraph drill → evidence panel.  
**Owns:** M4 `frontend/src/components/AlertTable.tsx` + `EvidencePanel.tsx` + `frontend/src/api/*` ; M5 `frontend/src/components/GraphView.tsx` (`cytoscape`), `GeoMap.tsx` (`leaflet`), `ReplaySlider.tsx` ; shared `frontend/src/cytoscape/*`. Never overlap files.  
**Flow:** Landing `GET /api/alerts?limit=50&sort=p` → `AlertTable` (columns: rank, wallet/txid, p, tier, why, geo) → click `alert_id` → `GET /api/graph/{alert_id}` (filtered subgraph 80-200 nodes/edges, `SELECT * FROM edges WHERE alert_id=?`) → `GraphView` cytoscape `cose-bilkent` preset layout (deterministic, no animation for >1K nodes) → `EvidencePanel` (geo timeline `Recharts`, amount Sankey, SHAP waterfall).  
**Cytoscape perf (F4):** <2K viewport → `preset` + `canvas` renderer + `hideEdgesOnViewport false`; 5K stalls even `hideEdges` (issue #292) → paginate server-side: `?limit=2000`. Sigma WebGL escape hatch if judge lasso >2K requested → swap `GraphViewSigma.tsx`.  
**Geo:** `Leaflet` + `OpenStreetMap` tiles bundled (offline via `mbtiles` or canvas fallback) — country/ASN centroid markers (city display-only per F3).  
**Replay:** `ReplaySlider` scrubs `timestamp` → `GET /api/replay?at={ts}` replays `edges` up to ts.  
**Stack:** React 19 + Vite 6 + `shadcn` + `cytoscape 3.30` + `cytoscape-cola`/`cose-bilkent` + `recharts` + `leaflet` + `fastapi` CORS.  
**API freeze:** `openapi.yaml` v1 — `GET /api/alerts`, `GET /api/graph/{id}`, `GET /api/evidence/{id}`, `GET /api/geo/{ip}`, `GET /api/mock/mempool`, `GET /api/replay`. M4 owns API shape, M5 reads.  
**Verifier:** `npm run bench:viz` → <2K preset >30fps, `npm run build && python -m http.server` offline check, `playwright test` click alert → graph renders <500ms.

### Part 9 — Offline Systems Engineering + Packaging — Owner: M6 Platform + You (Lead)
**Goal:** One-click air-gapped `docker compose up` → judges run on their laptops (Sameer 36h post).  
**Owns:** `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.web`, `scripts/build_wheels.sh`, `scripts/bundle.sh`, `wheels/`, `mmdb/` manifest, `.omo/plans/` (not needed — agent ad-hoc per ULTRAWORK but plan-gated momus locked? no plan file yet — lead owns `docker-compose.yml`).  
**Bundle manifest (USB):** `GeoLite2-City.mmdb 54MB + GeoLite2-Country 7MB + GeoLite2-ASN` + `models/gnn.pt 50MB + model_if.pkl 1MB + calibrator.pkl` + `data/raw/synthetic/synth_50k.csv (50K) + .json/.xml` + `wheels/*.whl` (quad: `--platform manylinux2014_x86_64 --python 3.11 --abi cp311 --implementation cp` × `torch cpu` + `torch rocm` + `pyg` + `geoip2` + `polars` etc. via `pip download --only-binary=:all:` vs `pip wheel` per Anchore/WeblineGlobal) + `node_modules` + `dist/` + `docker images` saved `docker save -o bundle.tar`.  
**Wheels:** `pip wheel` not `pip download` for build-deps (PyPI `Repeatable Installs` doc), quad `pip download --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all:` + `--no-index --find-links wheels/`. `BUILDKIT_PROGRESS=plain`.  
**Docker:** `docker-compose.yml` services: `api` (python:3.11-slim, `COPY wheels/ /wheels + pip install --no-index --find-links /wheels`, `COPY mmdb /app/mmdb`, `HEALTHCHECK CMD curl -f http://localhost:8000/api/health`), `web` (node:20, `npm ci --offline` from vendored `node_modules`), `network: internal: true` air-gapped, images by digest `image: api@sha256:...` (not tag) + auto-builds disabled, cold-start <3min.  
**Linux:** Ubuntu 22.04 LTS, `libmaxminddb` deb vendored, no `apt-get` at finale. ROCm fallback: Dockerfile `ARG DEVICE=gfx1100` → `RUN pip install torch[device-gfx1100] || pip install torch --index-url https://download.pytorch.org/whl/cpu` — always lands CPU.  
**Verifier:** On finale-class laptop (no wifi): `docker compose up -d && timeout 180 bash -c 'until curl -sf http://localhost:8000/api/health; do sleep 1; done' && curl -sf https://pypi.org --max-time 2 && echo FAIL || echo OFFLINE_OK` + `docker compose down -v` + cold-start timer <180s.

### Part 10 — Evaluation Harness & Write-Up (Really Important + UX Very Important) — Owner: M6 + You
**Goal:** Prove "working ML not just rules" + investigator-assist ethics, dual-track quantified.  
**Owns:** `scripts/eval/*` (pr.py, stress.py, drift.py), `data/eval/*` (pr.json, calibration.json, stress.json, fidelity.json), `docs/writeup.pdf`, `notebooks/demo.ipynb`, `model_card.md`.  
**Track A — Elliptic hold-out:** 70/30 temporal+graph-disjoint split (DFRWS builder) → PR-AUC, ROC, F1 vs rule baseline (XGBCLUS) — report PR-AUC Δ≥0.05 for hybrid win (Q1), else lead XGB 0.669 as SOTA (established 74-87%). Metrics: `pr_auc`, `fpr@90%tpr`, `ece`. Artifact: `data/eval/pr.json` + `pr_curve.png`.  
**Track B — Synthetic stress:** Inject 200 known illicit (peel/mixer/coinjoin/burst/bridge) into synth_50k → `detection_rate` + `fp_rate` — report `>90% @ <5% FPR` (Q20) — artifact `stress.json`.  
**Judge injection:** UI button `Inject peel chain` → `POST /api/inject {type:"peel", depth:5}` → immediate ranked alert (proves learning vs replay).  
**Fidelity sheet:** WITS 5-criteria (KS/NetSimile/DCR) + FinDiff column 0.954 if bank-style; AMLworld typology coverage. Artifact `fidelity.json`.  
**Write-up:** 6-page PDF (mermaid arch, model choice hedge, SHAP split, eval both tracks) + Jupyter `demo.ipynb` (ingest→graph→ML→SHAP cells runnable) + `model_card.md` (bias: CoinJoin FP, geo area hint p90 10×, Africa 66-72% failure, warrant note "investigator-assist not auto-freeze" per Chainalysis ontology, limitations, env `rocminfov1` + `duckdb v1.1`).  
**Verifier:** `python scripts/eval/pr.py --split dfrws --out data/eval/pr.json && python scripts/eval/stress.py --inject 200 --out data/eval/stress.json && make writeup` → PDF+notebook+card exist + `pr.json: hybridΔ` decides headline.

---

## §3 Decision-Gated Waits & 1-5 Sep Submit Checklist (7 Steps per recommendations.md §4)

| Step | Gate | Pass Criterion | Verifier | Deadline |
|------|------|----------------|----------|----------|
| 1 | Live PS text diff | `diff(description)` <5% Levenshtein + `dataset_link` not flipped empty→populated for 26146/26182 | `python scripts/fetch_sih.py` vs frozen `problem-statements.csv` s_no 146 | Daily 09:00 IST to 20 Sep |
| 2 | Org deployment re-check | NTRO HIGH 70-80% (23 PS, ≥13 winners) + MIC Report p3-4 + SAHYOG 35 VASPs PIB — not retracted to <5 PS | `review-orgs.md` Table §4 | Before hackathon |
| 3 | Already-built portal anti-clone | No NTRO live Bitcoin portal (only `worldmonitor.app` external) — write "WE DO THAT PORTAL DOES NOT" para per fetched portal | `curl worldmonitor.app + sih.gov.in PS → portal title diff` | Before hackathon |
| 4 | Hard-constraint | No hardware/IoT/sensor/embedded/UAV as core, no train-from-scratch beyond hosted/pretrained | rubric §2.5 keyword heuristic | Before hackathon — hard fail |
| 5 | Fresh wedge | FRESH (`J<0.30` + <2 tokens) — no GitHub SIH26146 replica; if re-audited RE-RUN, need new wedge (IP↔chain correlation) | `site:sih.gov.in + GitHub search "SIH26146"` | Before hackathon |
| 6 | Cap monitor | `submitted_count` <450 (alert ≥300 crowded, ≥450 risk, =500 FROZEN) — DataTables single-fetch 226 rows | `scripts/fetch_sih.py 09:00/18:00` + `git diff` | From 1 Sep to 20 Sep — submit 1-5 Sep |
| 7 | Air-gapped rehearsal | Both tracks air-gapped on finale laptops <3min compose up, 50K→alerts <14h, report <6h, 5-min window practice | `docker compose up --offline && time curl /api/health` + rehearsal log | Internal hackathon weekend before submit — also the only causal test H4 vs breadth |

All PASS → SUBMIT. Any FAIL → substitute via Top-10 lens (FRESH+PASS+org HIGH+already 0+demo 5-6+team 6) → next is SIH26102 MPLAD 7.8 / SIH26165 OIL SIF 7.4.

---

## §4 Source Discipline (Non-Negotiable)

Every winner/org/judge claim either has a verified live URL or is flagged `unknown` — no invented sources. Examples: NTRO 13 winners at `sih.gov.in/sih2024/sih2024-grand-finale-result` L3 + MIC Report L3 + DJ Sanghvi PDF L4; Shavitt 2011 PoP L2 + CAIDA/APNIC L4; DFRWS 2026 L2; Bhavesh repro L2; Kappos USENIX L2. Num confidence throughout (74-87% established, 38-68% contested). Contradictions C1-C8 preserved per Popper.

---

## §5 Follow-Up Questions After Research (Targeted, Post-Synthesis)

Synthesis flagged 3 P0 investigations that MUST be answered before you freeze code — these are the "ask me more questions after research" you requested. Answer via multiple-choice (I will update this file with your lock):


---

## §6 Post-Synthesis Locks (2026-08-23 — Answers to P0 Questions)

| P0 | Synthesis Risk | You Locked | Implementation |
|----|----------------|------------|----------------|
| ROCm Fallback | F5 18-28% full, 52-64% MP-only, 88-93% CPU | **CPU fallback default (safe)** | Bundle both wheel sets (`requirements.rocm.txt` + `requirements.cpu.txt`), Dockerfile `ARG DEVICE=cpu` default, entrypoint `torch.cuda.is_available()` probe only if `rocm-smi` exists. Finale runs CPU unless lab AMD box pre-tested. Verification: `pytest test_rocm_parity.py --device cpu` always PASS; `test_rocm_parity --device cuda` on your 7900GRE must show ≤1e-4 fp32 before Sep freeze else stay CPU. |
| Ingest+Viz SLA | F4 76-82% arch / 55-65% SLA contested | **Bench both this week on finale laptop** | `make bench` target: `python -m pytest tests/test_ingest.py -k "50k"` + `npm run bench:viz` (2K preset >30fps). Keep feature-flag `INGEST_ENGINE` and `VIZ_RENDERER=cytoscape|sigma`. Lock after bench, keep both code paths. |
| Network Hedge | F3 38-55% contested, GeoLite city 25-35% | **σ-sweep 5/30/120 + Country/ASN baseline** | `scripts/eval/sigma_sweep.py --sigmas 5,30,120` → `data/eval/sigma_sweep.json` (ΔPR-AUC @ each σ). Keep Country (99.8%)/ASN as feature (always), city display-only. If max Δ≤0.03, drop jitter feature and hedge as Country/ASN only in PDF. |
| Eval Headline | F1 42-58% hybrid lift contested | **Ablation table, no headline — let Δ speak** | PDF §Eval shows 3 rows: `XGB alone (0.669) / XGB+IF / Hybrid IF(0.4)+GNN(0.6)` on DFRWS leakage-free split + hold-out 30% + synthetic stress. No claim "Hybrid beats by 5pp" unless builder Δ≥0.05. Most defensible to wrapper-intolerant NTRO. |

All pending §1 rows now LOCKED post-synthesis. Update `DECISIONS.md §4` with these rows and commit.

