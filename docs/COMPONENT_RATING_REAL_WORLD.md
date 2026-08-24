# COMPONENT RATING — Real-World Readiness (NOT Synthetic Mock)

> **⚠️ EXPLICIT CONTRACT: NEVER ASSUME SYNTHETIC SUCCESS ⇒ REAL SUCCESS.**
> Every rating below evaluates whether the component works on **real on-chain blockchain data** with air-gapped constraints.
> Synthetic metrics (`pr_auc` on `synth_50k`, heuristic fallback Top-K) are **not predictive** of real Elliptic / Bitcoin Core / mempool performance.
> A component that scores 5 on synthetic data scores 1 here if its data dependency is synthetic-only.

**Generated:** 2026-08-24 from disk evidence (this checkout only, no invented metrics)

---

## 0. Synthetic vs Real Gap — Why This Document Exists

| Context | Edges | n | pr_auc | ECE | Source |
|---------|------:|---:|-------:|----:|--------|
| **Synthetic fallback (historical)** | **511** | 50K | **0.026** | — | previous `data/graph/duck.db` stub before elliptic anchoring (`audit_report.md` historical) |
| **Synthetic elliptic-anchored (current)** | **279,395** (50K p2p + 229K utxo + 1 temporal) | 50K sampled from 203K | **0.443** | **0.389** | `data/eval/pr.json:2` `pr_auc 0.443015`, `data/graph/duck.db` `SELECT count(*) FROM edges = 279395` |
| **Expected on real Elliptic++** | **234,356** Tx edges (ground-truth `elliptic_txs_edgelist.csv:1`) | 203K Txs / 49 timesteps | **~0.65** (deck claim) | — | `data/raw/elliptic/` `wc -l 234356`, deck `PROTOTYPE_DECISIONS_FINAL.md` hybrid 0.65-0.75 |

**Interpretation:**
- Historical 511-edge run (`pr_auc 0.026`) proves **synthetic topology under-produces real graph density** — it was a disconnected fallback, not a dataset.
- Current 279K-edge run (`pr_auc 0.443`) is **10× denser** but still synthetic p2p: 50K `src_ip→dst_ip` rows are from `ml/p2p_ips.py` Louvain→IP-pool hashing (`synth_50k_meta.json:7 n_unique_ips:5000`), not Bitcoin P2P `inv`/`addr` captures. The UTXO slice (229K) IS real-anchored (Elliptic BFS), which is why `pr_auc` rose from 0.026→0.443 — **but 0.443 ≠ 0.65**. Gap = 0.22 remains.
- `pr_auc 0.443` is **post-heuristic**: `ml/calibrate.py:_load_p_y` and `ml/infer.py:infer` inject `score=0.15+0.35*(fout>=5)+0.25*(fee>0.01)+… N(0,0.03)` when `|corr(p_raw,y)|<0.30`. Raw IF `corr(p_raw,y)=0.0015`, `score_samples` range `0.06` → heuristic rescues `corr→0.62`, `Top1000 100%` (`audit_report.md:49-54`). On real chain, `fout/fin/fee` are **real** but the heuristic's `0.35/0.25` weights are **synthetic-tuned** — unvalidated on real Elliptic `classes.csv` (46K labeled illicit, not `injection_label`).
- **Degradation across splits on same synthetic generator** (`data/eval/leakage.json`): `random 70/30 pr_auc 0.449 → temporal 0.443 (-0.007) → graph-disjoint 0.413 (-0.036)` — even synthetic→synthetic degrades. Cross-generator `seed42→seed999 sigma30→120` holds `0.456` (noise-stable) but that only proves hash jitter invariance, not real-world transfer.
- **Fidelity confirms gap:** `data/eval/fidelity.json` `ks 0.50` (threshold `ks<0.3` **false**), `netsimile 3.46` pass, `dcr 0.72` pass. `README.md:66` claiming `ks 0.078` is stale — disk says `0.50`. Synthetic graph is **not** indistinguishable from real.

**Conclusion:** Synthetic `0.443` is a **ceiling under synthetic label distribution** (7.7% illicit `injection_label`), not a floor for real. Real deployment must re-train on `elliptic_txs_classes.csv` (234K edges, 203K nodes) and re-evaluate — never carry `0.443` forward as "expected 0.65 will hold".

---

## 1. Component Rating Table (Real-World Readiness 1-5)

**Scale:** `1` = stub/synthetic-only, fails without real data/compute · `2` = partial, needs adapter/re-train · `3` = works but degraded without synthetic feed · `4` = production-viable with minor config · `5` = real-chain native, air-gapped ready.

| Component | What It Does | Data Required | Real On-Chain? | Synthetic-Only? | Rating (1-5) | Notes for Real Deployment (Air-Gapped, etc.) |
|-----------|--------------|---------------|----------------|-----------------|--------------|----------------------------------------------|
| **Ingest** (`backend/ingest/parsers.py`, `models.py`) | Auto-detect CSV/JSON/XML → Polars `scan_csv` + `sink_parquet` or DuckDB `COPY ... read_csv_auto` → `TransactionRecord` strict validate (100K-row batches) → quarantine `data/reports/validation.json` | CSV row with `txid(64 hex)`, `timestamp`, `src_ip/dst_ip`, `src_port/dst_port`, `input/output addresses+amounts`, `fee:float`, `script_type`, `geo_country/asn` | **Partial** — validation schema IS real Tx-faithful (Pydantic `strict=True`, `extra=forbid`, IPv4, fee float strict) | **No** — input is synthetic CSV (`data/raw/synthetic/synth_50k.csv`); no `bitcoind` RPC, `blocks/*.dat`, or `btcparser` adapter | **4** | Dual-engine parity 1.1× (`3.5s Polars vs 3.9s DuckDB` per `README.md`) is real. `INGEST_ENGINE` flag is air-gapped safe (no net). **Gap:** real chain needs new adapter: `bitcoin-cli getblock / getrawtransaction` → map to `TransactionRecord`; `src_ip/dst_ip` are **not in blocks** — ingest must mark P2P cols nullable or drop them for chain-only mode, else 100% `quarantined` on real blocks. `BATCH_SIZE 100K` + `watchdog` streaming holds for 234K edges (<3.5s). |
| **Graph — P2P layer** (`backend/graph/layers.py:86 build_p2p_edges`) | `src_ip → dst_ip` edge `type=p2p weight=1.0` per row, enrich `geo_asn` via `GeoEnricher.batch_lookup` | `src_ip`, `dst_ip`, `geo_country/asn` per Tx envelope | **No** — P2P IPs are **off-chain** mempool telemetry (requires `Bitcoin Core -listen` + `addr`/`inv` logs) | **Yes** — `ml/p2p_ips.py` `_scaled_pools` 5K IPs hashed from Louvain community → IP pool (`synth_50k_meta.json:7 n_unique_ips:5000`), `geo.py:_stub_for_ip` hash `lat=(h%180)-90` | **1** | On real chain **without P2P capture this layer is empty**. 50K p2p edges in `duck.db` are synthetic. Real air-gapped node can collect P2P **only** with `bitcoind` `debug=net` + custom `GeoEnricher` (`GeoLite2-City/ASN.mmdb` — currently `dist/mmdb/PLACEHOLDER 0B`, `data/geo/` empty per `evidence_map.md` #8). **Action:** mark P2P layer `optional`; Features that consume it (15/38) must degrade gracefully or be disabled in chain-only deploy. |
| **Graph — UTXO layer** (`layers.py:119 build_utxo_edges`) | Wallet→Tx→Wallet bipartite `type=utxo weight=amt/max_amt` via `input_addresses/output_addresses + amounts`, `fee` excluded, DAG per `txid` | `txid`, `input_addresses[]`, `output_addresses[]`, `input_amounts[]`, `output_amounts[]`, `fee` | **Yes** — pure on-chain, computable from `elliptic_txs_features.csv:1` or `bitcoind` `vout` | **No** | **5** | **Real-native.** Works on `elliptic_txs_edgelist.csv 234K` directly. Currently `data/graph/duck.db` `229,394 utxo edges` are BFS-sampled real UTXOs — valid. Air-gapped: no net needed, only `duck.db` + `schema.sql`. **Caveat:** `is_coinjoin` quarantine (`_coinjoin.py` Wasabi 20-in/20-out `within_1pct` + JoinMarket `0.4≤ratio≤0.7`) is heuristic on synthetic — real CoinJoin detection needs full block witness parsing. |
| **Graph — Temporal layer** (`layers.py:177 build_temporal_edges`) | Wallet reuse → Tx₁→Tx₂ `type=temporal weight=exp(-|dt|/300)` sorted `wt[wallet]`, collapse `|dt|>3600s` filtered, fallback single edge if empty | `timestamp` per Tx + `input_addresses` wallet linkage | **Partial** — timestamps ARE on-chain (`block time`) but `3600s` window + `exp(-s/300)` + fallback single edge are synthetic-tuned | **Partial** — DAG jitter `Exp(λ)+N(0, sigma=30)` from `ml/temporal.py`, not real `block.time` | **3** | **Works on real** `timestamp` but needs **real block time** not `Faker` jitter. Current `duck.db` `temporal=1` edge signals degenerate synthetic temporal (`audit_report.md` `1 temporal` of 279K) — real chain with 49 timesteps (Elliptic `time_step` 0-49) would produce `~40K` temporal edges (wallet reuse across 234K Txs). **Air-gapped:** `build.py:183-193` recomputes from `duck.db` edges — no net. Fix: use `elliptic` `time_step` or `bitcoind` `block.timestamp` verbatim, remove synthetic `sigma` jitter. |
| **Graph — Community** (`layers.py:248 build_communities`) | Louvain `community.best_partition(g)` on wallet co-spend graph (clique per Tx `inputs`), max-ratio `0.05` guard → linear fallback `comm[node]=i` | UTXO edges (wallet nodes) | **Yes** — Louvain on co-spend is standard real-chain analyst technique (wallet clustering) | **Partial** — hash fallback `abs(hash(txid))%50000` in `ml/infer.py:488` when `comm_map` misses | **3** | **Real-technique, synthetic-degraded.** With 234K real edges Louvain converges; with 511-edge fallback it collapsed (`max_ratio≥0.05` linearised all nodes — per `build.py:197-203`). Current 279K graph yields real communities (see `ml/graph_sampler.py`). **Air-gapped:** `networkx` + `python-louvain` bundled in `wheels/` scaffold (`dist/manifest.json:5k` planned) but `wheels/*/PLACEHOLDER` per evidence #8 — populate before offline deploy. |
| **Features (38 cols)** (`ml/features.py`) | Frozen `FEATURE_NAMES` 38D `float64` (15 network + 15 chain + 8 temporal) → `data/features/features.parquet (50000,38)` SHAP contract | See §2 below per-feature | **15/38** (~40%) — chain-only | **15/38** network + `modularity_delta` (hash) are synthetic-only | **2** | **11/38 degenerate `n_unique≤5`** (`tests/test_features_realistic.py:59` expects `≤8` — measured 11: `tor_flag 2, mixer_score 2, change_addr_likelihood 2, dust_outputs 2, op_return_flag 2, coinjoin_prob 2, peel_depth 2, script_type_hist_P2WPKH_ratio 2, burst_5m_count 4, p2p_burst_count 4, country_diversity 5`). Chain cols ARE real but 8 of 15 are binary flags (degenerate) — needs re-binning on real Elliptic distribution. Air-gapped: `duckdb`+`polars` only, but `_stub_for_ip` + `_hash_int` hash-fills mask missing P2P — on real chain these become **constant** (not hash-enriched). Must retrain IF/GNN on **real 38f** (elliptic 203K), not hash-padded. |
| **IF** (`ml/train.py` `IsolationForest(contamination=0.02, n_estimators=200)`) | Train `score_samples → p_if=1-1/(1+exp(raw))=sigmoid(-raw)` `offset_` threshold, LOF ablation `k=20` | 38f matrix `data/features/features.parquet` | **Partial** — IF is unsupervised, works on any numeric matrix; but learned **threshold** is contamination-tuned on synthetic prevalence `7.7%` (`2658/35000` train, `1203/15000` test) vs real Elliptic `~2%` (46000 labeled illicit of 203K ≈ `~22%` but `unknown` massive) | **Yes** — trained on hash-padded 38f; `corr(p_raw,y)=0.0015` before heuristic per audit | **2** | **Model exists (`models/if.pkl`) but not real-validated.** Raw `score_samples` span `0.06` (`audit_report.md:49`) → `p_if` narrow, rescue is heuristic (`ml/calibrate.py:230-276` `score` chain rule → `corr 0.62`, TopK 100%). On real Elliptic with 234K edges, contamination `0.02` mis-specifies true `~0.08` test prevalence. **Air-gapped:** `sklearn` pickled, no net, but must re-fit on **real 38f** (elliptic `features` not `synth_50k`), re-tune `contamination` to real `y` prevalence, drop heuristic fallback. Latency `fit <5s` (`max_samples=256`) is real-ready. |
| **GNN** (`ml/train_gnn.py` `M3_GCN 38→64→32→2 dropout 0.3`) | `GCNConv(38,64) → ReLU → Dropout(0.3) → GCNConv(64,32) → ReLU → Dropout → Linear(32,2)` `softmax(dim=1)[:,1]` `p_gnn`, `TORCH_BLAS_PREFER_HIPBLASLT=0` guard, `torch.load(...,map_location=cpu,weights_only=True)` | 38f nodes + `duck.db` edges `LIMIT 10000` `edge_index` via `hash(src)%num_nodes` | **Code yes, weights NO** — architecture is real-GNN ready (`pyg` `GCNConv`) | **Yes (weights)** — `models/gnn.pt` **`73B`** `pickle {state_dict:{}, config:{in:38,h1:64,h2:32,out:2}}` stub (`_ensure_dummy_pt`) per `evidence_map.md` #9 | **1** | **Least real-ready.** Architecture verified (reviewable), **zero trained parameters** — `fuse(0.4 IF + 0.6 GNN)` never inferenced with real weights. Kaggle T4×2 path `notebooks/kaggle_train_gnn.ipynb` is `PLAUSIBLE/UNVALIDATED` (not run offline). **Air-gapped:** requires `rocm/torch` wheels (currently `wheels/PLACEHOLDER` per #8) + `gnn_t4.pt` populated **online** then `bundle.tar 2.8G`. Until `cp ~/Downloads/gnn_t4.pt models/gnn.pt && make bundle`, ensemble weight `0.6` is unproven. Never report GNN `pr_auc` — use IF-only `0.443` as honest. |
| **Calibrate** (`ml/calibrate.py` Platt `FrozenEstimator` + Isotonic `clip`) | `CalibratedClassifierCV(cv="prefit", method="sigmoid")` 30% hold-out `stratify=y`, Isotonic challenger `out_of_bounds=clip`, `compute_ece(bin_edges linspace 0-1, 10 bins, |acc-conf|*n_bin/n)` `assign_tier p>0.90 Critical / 0.75 High / 0.50 Medium else Low` | `p_raw = 0.4*p_if+0.6*p_gnn` + `y` (`injection_label!=normal → 1`) | **Partial** — Platt/Isotonic math is real, but `y` is **synthetic** `injection_label` | **Yes** — `ece 0.389` on heuristic `p_raw`, `prob_true [0.064,0.777] prob_pred [0.456,0.511]` 2-bin collapse (`data/eval/calibration.json:2`) | **2** | `models/calibrator.pkl 1.9K` Platt is real `sklearn` artifact, air-gapped load via `pickle` works offline. But `0.389 ECE` is **not** `README.md:68` `platt_ece 0.007` — stale. On real Elliptic `classes.csv` (46K labeled), prevalence + `p_raw` distribution differ → re-calibrate on **real labels** 30% hold-out. Tier thresholds `0.90/0.75/0.50` are policy constants (grepped) — real `prec@tier` unknown until real `pr.json` re-run. |
| **Ensemble (0.4/0.6)** (`ml/ensemble.py` `fuse`, `sigmoid_if`, `softmax_gnn`, `XGB_SOTA 0.669`) | `sigmoid_if: p_if=1/(1+exp(raw))` (raw `score_samples`), `softmax_gnn: softmax(logits)[:1]`, `fuse: 0.4*p_if+0.6*p_gnn` (numpy + `pl.Series` paths), `hedge_decision delta<0.05 → XGB` | `p_if` + `p_gnn` (or fallback random `N(0,1)`) | **Partial** — `0.4/0.6` are config literals, not grid-searched on real `pr_auc` | **Yes** — no `XGBoost` trained (`maybe_train_xgb` returns `None`), `XGB_SOTA 0.669` is an external benchmark constant, never measured here | **1** | `fuse(0.6,0.8)==0.72` unit passes, but **ensemble `pr_auc` never measured**: `ml/train.py:46` IF-only, `ml/train_gnn.py:73B` stub, so `0.4/0.6` is **untested on real**. `hedge_decision` would fire on current `delta=0.443-0.669=-0.22<0.05` → hedge to (non-existent) XGB. **Air-gapped:** pure numpy, offline-safe, but weight choice must be re-tuned via `scripts/eval/pr.py` + `stress.json` on **real 234K** — never assume `0.6 GNN` helps when GNN is stub. |
| **Explain** (`ml/explain.py` SHAP + Jinja + GNNExplainer cached) | `shap.TreeExplainer(IF).shap_values (n,38) → argsort(|sv|)[-3:][::-1]` top-3, `jinja2.Template("Wallet {{addr}} flagged: {{fan_out}} outputs <1 BTC in {{burst}} min… conf {{p}} ({{feat1}}+{{feat2}}+{{feat3}})")` NL, `GNNExplainer epochs=200` async `lru_cache(1024)` + `data/alerts/gnn_explain_cache.json` | `models/if.pkl`, `data/features/features.parquet`, `data/alerts/ranked.parquet` | **Partial** — SHAP math is real, but feature importances are over **hash-padded synthetic** distributions | **Partial** — `GNNExplainer` never executed (attention fallback hash), cache `150K×3 nodes` | **2** | SHAP latency `5-30ms` is cached synthetic (`_compute_shap_top3` fallback `rng.standard_normal(50000,38)` when `shap` missing). NL template renders but `fan_out/burst` values are hash-enriched (`features.py` `burst_5m_count` hash `1+(h%4)`). On real chain with chain-only 38f, SHAP top-3 will be **different features** (likely `fan_in/out`, `fee_sat_per_vb`, `peel_depth`) — current NL is synthetic-biased. **Air-gapped:** `shap`+`jinja2` wheels needed (`wheels/` scaffold) — otherwise fallback deterministic. |
| **Trace** (`ml/explain.py:get_gnn_subgraph` + `data/alerts/*`, `frontend/src/components/GraphView.tsx`) | Per-`alert_id` `nodes=[alert_id, node_h%1000, node_(h//1000)%1000] edges=[[0,1],[1,2]] attention=[h%100/100,…] epochs=200` + `data/alerts/gnn_explain_cache.json 71M/150K` + `explanations.json` subgraph stubs | `alert_id` hash only (no `duck.db` BFS) | **No** — no BFS over `utxo+temporal` edges, no `GET /api/graph/{alert_id}` route (`audit_report.md:129` `404`) | **Yes** — every entry 3 nodes/2 edges, never `80-200` | **1** | **Least trace-like.** `GraphView.tsx` renders up to `2K` mock, not BFS. Real trace requires `duck.db` walk: `SELECT * FROM edges WHERE type IN ('utxo','temporal')` BFS depth 2-3 from `txid` → `80-200` nodes. Current `backend/graph/build.py` *creates* that graph (279K edges) but `explain.py` **does not query it** — `get_gnn_subgraph` hashes `alert_id`. **Air-gapped:** feasible offline (pure `duckdb` + `networkx`), but missing API blocks demo. Fix: implement `GET /api/graph/{txid}` BFS in `backend/main.py` before claiming `80-200`. |

---

## 2. Feature-Level Classification — 38 Frozen SHAP Features (`ml/features.py:29 FEATURE_NAMES`)

**Method:** read `ml/features.py:_build_features` (1002 lines). Each feature's data source classified from code + `data/raw/synthetic/synth_50k.csv` columns.

| # | Feature | Category | Code Dependency (`ml/features.py:line`) | Real On-Chain? | Synthetic/Network? | Notes if Real Deploy Omits P2P Feed |
|---|---------|----------|------------------------------------------|----------------|--------------------|-------------------------------------|
| 1 | `unique_peers` | Network (15) | `:536` `wallet_to_peers ∪ ip_to_peers` union + hash `extra=10+(h%491)` if `≤2` | No | **Synthetic** — P2P `src_ip/dst_ip` union | On real chain without P2P → hash-filled `10-500`, meaningless. Disable or mark `null`. |
| 2 | `asn_entropy` | Network | `:558` `_wallet_or_community_fallback(wallet_asns, ip_asns)` + `hash` padding | No | **Synthetic** — `geo_asn` + `_stub_for_ip` `abs(h)%60000+1000` | Falls back to `ip_to_asns` hash — collapses to `~0.69` without real GeoLite2. |
| 3 | `port_entropy` | Network | `:572` `wallet_to_ports ∪ ip_to_ports` `hash` `“%65535` | No | **Synthetic** — `src_port/dst_port` | `8333` default + hash jitter `h%100/1000` — no real P2P port entropy. |
| 4 | `geo_distance_variance_km` | Network | `:586` `haversine_km(lat1,lng1,lat2,lng2)` over `tx_indices` + `50+(h%7950)` if `0` | No | **Synthetic** — `_stub_for_ip` `lat=(h%180)-90` | Computes haversine on hash lat/lng — variance is `h%1000+50/10` synthetic. Requires real `GeoLite2` + real IPs. |
| 5 | `inv_jitter_std` | Temporal-ish (Network) | `:628` `std(intervals)` of `wallet_to_times ∪ ip_to_times` + hash `300+(h%700)` | No | **Synthetic** — intervals from `timestamp` but hash-padded `inv` label overstates P2P `inv` | Uses `timestamp` (real) but `inv` semantics require mempool `inv` timestamps — block times are coarser. |
| 6 | `peer_degree` | Network | `:648` `ip_degree[src_ip]+ip_degree[dst_ip]` from `edges type=p2p` else hash `1-10` | No | **Synthetic** — p2p edge counts | `0` → `h%10+1` synthetic. |
| 7 | `asn_hopping_rate` | Network | `:657` `hops/(n-1)` via `_stub_for_ip` ASN mismatch + haversine `>1000km` + hash `0-0.8` | No | **Synthetic** — ASN + geo stub | Without real ASN, `hopping_rate` is `h%80/100` random. |
| 8 | `port_anomaly_score` | Network | `:704` `abs(sp-8333)/8333 + abs(dp-8333)/8333 + h%100/1000` | No | **Synthetic** — ports vs `8333` | `8333` is protocol default — not anomaly on real `testnet`/`regtest`. |
| 9 | `country_diversity` | Network | `:713` `wallet_to_countries ∪ ip_to_countries` `len(set)` + `1+(h%5)` if `≤1` | No | **Synthetic** — `_stub_for_ip` `country` `US if lat>0 else DE` | `US/DE` hash binary — real GeoLite2 would give `~250` countries. |
|10 | `p2p_burst_count` | Network | `:735` `count(|t-ts|≤300s)` over `times_w` + `1+(h%4)` | No | **Synthetic** — `times_w` from `timestamp` but `p2p` burst semantics | Real burst needs mempool arrival times, not `block.timestamp`. |
|11 | `rtt_proxy_ms` | Network | `:764` `abs(hash(src+dst))%200+20+h%30` | No | **Synthetic 100% hash** | Pure hash `20-250ms` — impossible without real P2P `ping`/`rtt`. Must drop for chain-only. |
|12 | `uptime_hours` | Network | `:768` `(max(times_w)-min(times_w))/3600 + h%50/100` else `h%120+10/60` | Partial | Synthetic fallback | `times_w` is real if present but `uptime` semantics require `peer` session logs. |
|13 | `tor_flag` | Network | `:783` `_is_private_ip(src_ip) or _is_private_ip(dst_ip)` `10/192.168/172.16/127` | No | **Synthetic** — private IP hash | `synth_50k` IPs are random public; `tor_flag` fires only on `10.*` etc — hash undercounts real Tor exit nodes. |
|14 | `accuracy_radius_mean` | Network | `:786` `mean(wallet_to_radii ∪ ip_to_radii)` `_radius_for_ip` `50+(h%251)` | No | **Synthetic** — `GeoLite2` accuracy_radius hint | Comment `hint only — do not use in WHERE` (`geo.py:1-5`). Real radius needs `GeoLite2-City.mmdb` (0B placeholder). |
|15 | `ws_reconnects` | Network | `:796` `abs(hash(primary))%7` `0-6` | No | **Synthetic 100% hash** | WebSocket `reconnects` require off-chain infra logs — never on-chain. Drop. |
|16 | `fan_in` | Chain (15) | `:798` `len(input_addresses)` | **Yes** | No | Real `vout` — always available. |
|17 | `fan_out` | Chain | `:799` `len(output_addresses)` | **Yes** | No | Real — but synthetic heuristic `fout>=5` drives TopK (`ml/infer.py:403`). |
|18 | `output_amount_variance` | Chain | `:813` `_variance(out_floats)` + hash `h%100/1000` if `0` | **Yes** | Partial hash pad | Real `value_median` + amounts — core on-chain. |
|19 | `fee_sat_per_vb` | Chain | `:820` `fee*1e8/250` | **Yes** | No | Real `fee` (strict `float` in `TransactionRecord`) — `fee>0.01` heuristic-sensitive. |
|20 | `script_type_hist_P2WPKH_ratio` | Chain | `:821` `1 if script_type=="P2WPKH" else 0` | **Yes** | No | Real `script_type` `Literal["P2PKH","P2SH","P2WPKH","P2WSH","unknown"]` — but degenerate `n_unique=2`. |
|21 | `input_count` | Chain | `:822` `fan_in` alias | **Yes** | No | Duplicate of `fan_in` (collinear). |
|22 | `output_dispersion_gini` | Chain | `:823` `_gini(out_floats)` | **Yes** | No | Real Gini — `max<1 BTC` heuristic `+0.1` in `ml/infer.py:415` is synthetic-tuned. |
|23 | `utxo_age_blocks` | Chain | `:824` `abs(hash(txid))%1000` | No | **Synthetic hash** | Claims blocks but is `h%1000` hash — not `block.height - tx.height`. Requires `gettxout` + block index. **Fix:** compute from `block.height`. |
|24 | `peel_depth` | Chain | `:825` `1 if len(w)==1 and len(out)==2 else 0` | **Yes** | No | Real peel heuristic — degenerate `2`. |
|25 | `mixer_score` | Chain | `:826` `len(w)>=3 and len(out)>=3 and var<0.01` | **Yes** | No | Real mixer heuristic — degenerate `2`. |
|26 | `coinjoin_prob` | Chain | `:829` `is_coinjoin(tx_dict)` `Wasabi 20/20 within_1pct` | **Yes** | No | Real `is_coinjoin` (`_coinjoin.py`) — degenerate `2`. |
|27 | `change_addr_likelihood` | Chain | `:844` `max-min/max>0.5` if `len==2` | **Yes** | No | Real — degenerate `2`. |
|28 | `dust_outputs` | Chain | `:853` `count(x<0.00005)` + hash `h%20==0→1` | **Yes** | Partial hash | Real dust ` <546 sat` but synthetic threshold `0.00005 BTC`. |
|29 | `op_return_flag` | Chain | `:858` `0 if script_type in P2* else 1` | **Yes** | No | Real — degenerate `2`. |
|30 | `value_median` | Chain | `:860` `_median(all_vals)` | **Yes** | No | Real median — `value_median` drives `amount_params.json` `lognormal` per-label synthetic anchoring. |
|31 | `burst_5m_count` | Temporal (8) | `:755` `count(|t-ts|≤300)` (alias `p2p_burst_count`) | Partial | Partial | Real if timestamps present, but degenerate `n_unique=4` hash `1+(h%4)`. |
|32 | `burst_1h_count` | Temporal | `:758` `count(|t-ts|≤3600)` + `c5+h%5` | Partial | Partial | Similar — `n_unique=8` borderline. |
|33 | `inter_tx_interval_std` | Temporal | `:646` alias `inv_jitter_std` | No | **Synthetic alias** | Duplicate of #5. |
|34 | `modularity_delta` | Temporal | `:863` `((h%2000)-1000)/2000` `-0.5..0.5` | No | **Synthetic 100% hash** | Pure hash — no Louvain delta computed. Drop or compute `Q_before-Q_after` from `community_size`. |
|35 | `hour_entropy` | Temporal | `:868` `_entropy(hours)` with `h%24` synthetic `3-5` hours if `0` | Partial | Partial hash-padded | `hours = times_w.hour` is real but hash-injects `3` distinct hours on degenerate single-tx wallets (`entropy 0→~1.0`). Real chain with 49 Elliptic steps has coarser timestep granularity. |
|36 | `day_of_week_entropy` | Temporal | `:893` `_entropy(dows)` with `h%7` synthetic if `0` | Partial | Partial hash-padded | Same as #35. |
|37 | `community_size` | Temporal | `:908` `comm_size_map[cid]` else `20+(h%781)` | Partial | Hash fallback | Real if `nodes.community_id` from Louvain; fallback `20-800` hash. |
|38 | `betweenness_z` | Temporal | `:916` `bet_map[wallet]` z-score else `(h%4000-2000)/800` | Partial | Hash fallback | Real via `networkx.betweenness_centrality` on `utxo+temporal` DiGraph (up to `5000` nodes exact, `k=200` sampled above), else hash `-2.5..2.5`. |

**Count:** `Network 15 = 100% synthetic/hash` · `Chain 15 = 14 real + 1 hash (utxo_age_blocks)` · `Temporal 8 = 1 pure hash (modularity_delta) + 5 hash-padded + 2 real-community hash-fallback`.

**Degenerate 11** (`n_unique≤5`) all fall in synthetic or hash-padded groups — `tests/test_features_realistic.py:59` fails `≥30 with n_unique>5` (measured `27`).

---

## 3. Detailed Per-Component Deep Dive

### 3.1 Ingest — `backend/ingest/parsers.py` + `models.py`

**What it does:** §1 table already. `detect_format` via `python-magic` → `mimetypes` → `ext` fallback; `validate_batched` strips `injection_label/risk_tier` before `TransactionRecord.model_validate(strict=True, extra=forbid)`; quarantine append via `tempfile.mkstemp` + `os.replace` atomic.

**Real data it consumes:** `src_ip/dst_ip/src_port/dst_port/geo_*` are **not in Bitcoin blocks** — they are synthetic envelope cols added by `scripts/generate_synthetic.py` to exercise P2P. Real `Bitcoin Core` block is `txid + inputs(prev_hash, prev_n) + outputs(address, value) + locktime + script`, plus `block.timestamp/height`. Fees are `SUM(inputs)-SUM(outputs)` (not a stored field). `TransactionRecord.fee:float` strict (`fee must be float` guard in `models.py:44`) would reject real `Decimal`/satoshi int without coercion.

**Whether it works on real blockchain data:** **Yes with adapter** (rating 4). Polars `sink_parquet` and DuckDB `COPY` paths handle `50000` rows `<2000ms` per `data/eval/bench_ingest.json csv p50_ms 2019.06`. Strict validation is air-gapped friendly (no network). **Fails** on real raw blocks unless you pre-map `block → TransactionRecord` (resolve `prev_hash` to address via UTXO index, compute `fee`, synthesize `src_ip=0.0.0.0` or drop cols).

**Evidence:** `du -sh data/raw/elliptic 666M` exists — but `grep -r "BTC_DATA" --include="*.py" ml/ scripts/ | wc -l = 0` shows no eval consumes real `BTC_DATA.csv 4389 rows, 25M` (daily aggregates, no `txid`).

### 3.2 Graph — 4 Layers (`backend/graph/layers.py`, `build.py`)

**P2P (rating 1):** consumes 0 on-chain bytes. `build_p2p_edges` loops `df iter_rows` → `1.0 weight` per row, never touches `utxo`. `GeoEnricher` doc `radius hint only — do not use in WHERE/HAVING` confirms radius is display hint. Air-gapped `GeoLite2` missing → `_stub_for_ip` hash.

**UTXO (rating 5):** consumes `input_addresses/output_addresses/amounts/fee`. Code `amt/max_amt` normalized per batch. Fully deterministic, no hash fallback. 229K edges prove it scales to 234K.

**Temporal (rating 3):** consumes `timestamp` + `input_addresses` wallet linkage. `temporal_weight dt = exp(-|s|/300)` is honest decay but `300s` is synthetic (Bitcoin `block_time 600s` + `mempool` variance differs). `1 temporal edge` in current `duck.db` signals wallet reuse across 50K sampled Txs is sparse — real 203K chain with 49 timesteps would densify.

**Community (rating 3):** consumes wallet co-spend graph `G.add_edge(wallets[i], wallets[j])` per Tx. `Louvain best_partition` is real Walktrap modularity, but `build.py:200` `max(cnt)/sum(cnt) >=0.05 → linearize` trips on degenerate 511-edge case — on 279K graph it preserves structure. Air-gapped: `community_louvain` optional (`try import`), fallback `enumerate(g.nodes())`.

### 3.3 Features 38 — already classified §2 (rating 2)

**Key line:** `features.parquet (50000,38) float64×38` (`data/features/feature_names.json:2` length 38). Order frozen per SHAP contract (`ml/features.py:29-67`). `data/eval/fidelity.json` `ks 0.50` fail proves hash-padded `unique_peers 10-500` and `geo_distance_variance` etc are **not** drawn from real `GeoLite2` distribution — they are `h%7950` uniforms.

**Air-gapped:** pure `polars+duckdb+hashlib` — no network at build time. But future real run must disable 15 network cols or fix `GeoEnricher` `mmdb` population (`scripts/build_wheels.sh` online → bundle).

### 3.4 IF — `ml/train.py` (rating 2)

**What `train_if` does:** `IsolationForest(contamination=0.02, n_estimators=200, max_samples=256, max_features=1.0, bootstrap=False, n_jobs=-1)` → `fit` (`elapsed<5s` asserted) → `score_samples → p_if=1-1/(1+exp(raw))` same as `ensemble.sigmoid_if` `1/(1+exp(raw))`.

**Data dependency:** `data/features/features.parquet` or fallback `rng.standard_normal(50000,38)` (`_load_features:93`). That fallback `0.02 contamination` threshold is **contamination≠prevalence** — synthetic test `prevalence 0.0802` (`pr.json n_pos_test 1203/15000`) mismatches `0.02` → `offset_` threshold mis-calibrated; heuristic rescues.

**Real-world:** IF is unsupervised, so **it will run** on real 38f — but its `decision_function < offset_` boundary is **not** learned illicit boundary. On real Elliptic where `illicit≈22%` of labeled, `contamination 0.02` would label `98%` `normal`. Must re-tune `contamination ≈ real prevalence` and re-evaluate `pr_auc` — never assume `0.443` transfers.

### 3.5 GNN — `ml/train_gnn.py` `M3_GCN` (rating 1)

**Architecture verified:** `GCNConv(38,64) + Linear(32,2) dropout 0.3` per `ml/train_gnn.py:63-76`, `TORCH_BLAS_PREFER_HIPBLASLT` sentinel per `51-55` (grep-required), `torch.load(...,map_location=cpu,weights_only=True)` per `208`.

**Data dependency:** `edge_index` from `duck.db SELECT src,dst LIMIT 10000 → hash(src)%num_nodes` (`_build_edge_index:148-157`) — synthetic hash edges, not `edge_type=utxo/temporal` adjacency. Training fallback `_build_edge_index` chain+self-loops (`src=[0..n-2]+[0..n-1]`) is disconnected from real 234K topology.

**Weights:** `models/gnn.pt 73B` empty. `get_model()` exists but `predict_proba` on stub raises `CPU fallback`. Ensemble `0.6` is **dead weight** until `gnn_t4.pt` populated via `notebooks/kaggle_train_gnn.ipynb` `200 epochs T4×2`.

**Air-gapped:** needs `torch+pyg` wheels (`wheels/` `PLACEHOLDER` per evidence #8) + CUDA `rocm` if `gfx1100`. `make bundle` `2.8G 163 blobs` scaffold ready but wheels not populated offline.

### 3.6 Calibrate — `ml/calibrate.py` (rating 2)

**Platt** `FrozenEstimator(wrapper)` `method=sigmoid` via `CalibratedClassifierCV` (`_load_p_y` heuristic when `|corr|<0.30`), **Isotonic** `out_of_bounds=clip` challenger. `train_test_split(test_size=0.30, stratify=y, random_state=42)` per docstring (`calibrate_and_evaluate:298`). `compute_ece` `linspace 0-1 11 edges` weighted `|acc-conf|*n_bin/n`.

**Real data:** `y` is `injection_label != normal → 1` from `data/raw/synthetic/synth_50k.csv` — synthetic `4%` illicit mix, not `elliptic_txs_classes.csv` `unknown/illicit/licit` ternary. `p_raw` is `1 - 1/(1+exp(score_samples))` **or** heuristic `0.15+...` stretched `0.2-0.8` if narrow.

**Measured:** `platt_ece 0.389`, `iso_ece ≈0.389`, `prob_true [0.064,0.777] prob_pred [0.456,0.511]` 2-bin — `brier_platt` computed but not gated.

**Air-gapped:** `pickle` `payload {platt, isotonic, ece, method, platt_ece, isotonic_ece, bins:10}` → `models/calibrator.pkl 1.9K` offline load in `ml/infer.py:_calibrate_p`. Tier `Critical>0.90` etc is policy — but `Prec(Critical)` on real unknown until re-run.

### 3.7 Ensemble (0.4/0.6) — `ml/ensemble.py` (rating 1)

**Literally:** `W_IF=0.4 W_GNN=0.6` literals grepped, `fuse = s_if*0.4 + s_gnn*0.6` for both `pl.Series` and `np.ndarray` paths. `XGB_SOTA=0.669` constant, `hedge_decision delta<0.05 → XGB`. `softmax_gnn` tries `torch.softmax` then numpy `exp(arr-m)/sum` fallback (`softmax` literal kept for grep).

**Data:** `p_if` from `score_samples` (narrow) + `p_gnn` from random `N(0,1) (n,2)` logits → `softmax_gnn` when stub. So `p_raw = 0.4*0.6-ish + 0.6*Uniform(0,1)` ≈ `0.42±0.17` — synthetic uniform mixture, not learned fusion. Heuristic in `infer.py:377-422` replaces `p_raw` entirely when `corr<0.30` with `heur2+ N(0,0.03)` chain rule — the `0.4/0.6` is **bypassed** in that branch.

**Real-world:** weight `0.4/0.6` never grid-searched vs `pr_auc` on real hold-out. On real 234K where GNN stub gives random `p_gnn`, `0.6` weight **hurts** (amplifies noise). Needs `scripts/eval/pr.py` sweep `w∈[0,1]` on real `elliptic` split.

### 3.8 Explain — `ml/explain.py` (rating 2)

**Top-3:** `shap.TreeExplainer(model).shap_values (n,38) → argsort(|sv|)[-3:][::-1]` per `tests/test_features_realistic.py` expectation. Fallback `rng.standard_normal((n,38))` when `shap` absent. **NL:** `jinja2.Template("Wallet {addr} flagged: {{fan_out}} outputs <1 BTC… conf {{p_formatted}} ({{feat1}}+{{feat2}}+{{feat3}})")` must contain `Wallet`+`flagged` grep.

**Real data:** `fan_out_i=int(feat_mat[fan_out_idx])` `burst_i`, `countries_i`, `asn_hopping:.2f` pulled from `feat_mat` (hash-padded). `addr` from `ranked.wallet/txid` or `synth_50k.csv input_addresses[0]` or `bc1q_synth_*`. Confidence `p_formatted:.2f` is `p_calibrated`.

**Latency claim 5-30ms** via `lru_cache(1024)` + `data/alerts/gnn_explain_cache.json` file-cache (`_gnn_explain_cached_inner`). Measured file `71M 150K` but `await asyncio.sleep(0.01)` simulates `1-3s` — CI-fast, not prod P50.

**Air-gapped:** `shap` optional — fallback deterministic ensures offline `explain` without `shap` wheel. `jinja2` similarly optional (`str.format` fallback). Real SHAP values will shift to chain features when P2P cols disabled — NL template's `outputs <1 BTC` heuristic (`max<1 BTC +0.1` in `infer.py`) is synthetic-biased.

### 3.9 Trace — `ml/explain.py:get_gnn_subgraph` + `frontend/src/components/GraphView.tsx` (rating 1)

**What trace is (claimed):** `80-200 nodes` per alert `utxo+temporal` BFS from `txid` → `community_size` + `betweenness_z` subgraph, `GET /api/graph/{alert_id}` per `audit_report.md:129`.

**What trace is (measured):** `nodes=[alert_id, "node_0765","node_0422"] edges=[[0,1],[1,2]] attention=[0.5,0.42] epochs=200` — `3 nodes` hash per `explain.py:362-374`, `data/alerts/gnn_explain_cache.json 150K entries` every `3 nodes`, `data/alerts/explanations.json[0].subgraph` `3 nodes`. No `GET /api/graph` route in `backend/main.py` (404). `GraphView.tsx` caps `2K` mock.

**Real data:** `duck.db` already has `279K` edges to support BFS — but `get_gnn_subgraph` never queries `duck.db` (`explain.py:340` `get_gnn_subgraph` does `cache.get(alert_id)` only). `backend/graph/build.py` `betweenness_centrality + pagerank` is computed on `DiGraph utxo+temporal` during build — trace could reuse that graph instead of hashing.

**Air-gapped:** fully offline-capable — `duck.db` + `networkx DiGraph` BFS is local. **Fix:** implement `backend/api/ingest.py`-style route `GET /api/graph/{txid}?depth=2&limit=200` that `SELECT src,dst FROM edges WHERE type IN ('utxo','temporal') BFS` and return `nodes/edges` sized `80-200`; update `GraphView.tsx` to fetch it instead of `explanations.json` stub.

---

## 4. Air-Gapped Deployment Implications

- **Compose:** `docker-compose.yml:18-64` `network:{internal:true}`, `HEALTHCHECK curl -f http://localhost:8000/api/health`, `Dockerfile.api:1,6,9,28` digest-pinned `python:3.11-slim-bookworm@sha256:2e32f…` + `COPY wheels/ /wheels` — **verified scaffold**.
- **Bundle:** `bundle.tar 2.8G 163 blobs` `bundle/README.md` + `dist/manifest.json {wheels_count:5, mmdb_count:0, models_count:1}` — **verified scaffold**.
- **Blockers:** `dist/mmdb/PLACEHOLDER 0B`, `data/geo/` empty, `wheels/{common,cpu,rocm}/PLACEHOLDER+README` — real `.whl` not populated offline; `GeoLite2-City.mmdb/ASN.mmdb` missing (MaxMind CC BY-SA 4.0 EULA) — `GeoEnricher` falls back to hash even air-gapped.
- **Models:** `models/if.pkl` + `models/calibrator.pkl 1.9K` are real artifacts; `models/gnn.pt 73B` is stub — `kaggle_train_gnn.ipynb T4×2 200 epochs 15-25min` must run **online** then `cp ~/Downloads/gnn_t4.pt models/gnn.pt && make bundle` per `README.md:68`.
- **What to ship chain-only:** disable P2P layer + 15 network features + `ws_reconnects/rtt_proxy_ms` (hash-only) — ship 23-feature chain+temporal model (`fan_in` etc + `burst/hour_entropy/community_size/betweenness_z`). Document reduced `Expected pr_auc ≈0.35-0.40` (drop from `0.443` heuristic) until real P2P feed available.
- **Timed validation not yet measured:** `docker load -i bundle.tar && timeout 180 bash -c 'until curl -sf http://localhost:8000/api/health; do sleep 1; done'` on finale laptop is **plausible/UNVALIDATED** per evidence #8 — must time before claiming `<3min`.

---

## 5. What To Do Next — Before Claiming Real-World Performance

1. **Elliptic-native features:** `ml/features.py` → fix `utxo_age_blocks = block.height - tx.height` (not `h%1000`) via `elliptic_txs_classes.csv time_step + edgelist`, or drop `modularity_delta` from `hash` to `Q(louvain) delta`.
2. **Retrain IF on real 38f:** `ml/train.py --features data/elliptic/features.parquet` (203K rows, not 50K synth) with `contamination = prevalence(elliptic)` and no heuristic `corr<0.30` branch.
3. **Populate GNN:** run `notebooks/kaggle_train_gnn.ipynb` on `T4×2` with `edge_index` from real `utxo+temporal` (not hash), 200 epochs, `TORCH_BLAS_PREFER_HIPBLASLT=0 gfx1100`, then export `gnn_t4.pt`.
4. **Sweep ensemble weight:** `ml/ensemble.py` `w_if∈[0,1]` grid vs real `pr_auc` (not `0.4/0.6` literal) — report `best w` and `Δ vs IF-only`.
5. **Re-calibrate on real labels:** `ml/calibrate.py --p_raw data/elliptic/p_raw.parquet` (elliptic `classes.csv illicit?1:0`) 30% hold-out, report `ece` (expect `0.05-0.10`, not `0.389`) and tier `Prec/Rec`.
6. **Implement trace BFS:** `backend/main.py GET /api/graph/{txid}` `duck.db` walk depth 2, return `80-200` nodes; wire `GraphView.tsx` to it; delete hash stub.
7. **Populate offline bundle:** online host `scripts/build_wheels.sh --quad pip download` → real `.whl` + `GeoLite2 *.mmdb` into `wheels/` `mmdb/`, then `make bundle` and timed `docker load+compose up` test.

---

## 6. Verifier — Copy-Paste for This Checkout

```bash
# Features & degenerate
cat data/features/feature_names.json | jq length  # 38
python3 -c "import pyarrow.parquet as pq; df=pq.read_table('data/features/features.parquet').to_pandas(); print(df.shape); print('degenerate<=5:', (df.nunique()<=5).sum()); print(df.nunique()[df.nunique()<=5].to_dict())"
#  (50000,38)  11  tor_flag:2 ... burst_5m_count:4

# Graph edges (real-anchored vs synthetic p2p)
python3 -c "import duckdb; c=duckdb.connect('data/graph/duck.db',read_only=True); print(c.execute('SELECT type,count(*) FROM edges GROUP BY type').fetchall()); print(c.execute('SELECT count(*) FROM edges').fetchone()); print(c.execute('SELECT count(*) FROM nodes').fetchone())"
#  [('temporal',1),('utxo',229394),('p2p',50000)]  (279395,)  (284394,)

# PR-AUC honest (do NOT report 0.65/0.58)
cat data/eval/pr.json | jq .pr_auc, .ece, .fpr_at_90_tpr, .split, .n_pos_test
#  0.44301508329693895 0.3893589700159114 0.6114372689715155  "dfrws"  1203
cat data/eval/leakage.json | jq '.[] | {split:.split, pr_auc:.pr_auc}'

# Heuristic rescue audit
python3 -c "import polars as pl, numpy as np, pickle; df=pl.read_parquet('data/features/features.parquet'); import json; s=pl.read_csv('data/raw/synthetic/synth_50k.csv'); y=np.array([0 if str(v)=='normal' else 1 for v in s['injection_label'].to_list()]); clf=pickle.loads(open('models/if.pkl','rb').read()); raw=clf.score_samples(df.select(df.columns[:38]).to_numpy()); p=1-1/(1+np.exp(raw)); print('corr(p_raw,y)=', float(np.corrcoef(p,y)[0,1]), 'raw_span', float(np.max(raw)-np.min(raw)))"
#  0.0015  0.06  -> heuristic active per ml/infer.py

# Calibration stale vs disk
cat data/eval/calibration.json | jq .ece, .prob_true, .prob_pred
cat README.md | grep -n "ece platt"  # stale 0.007 vs disk 0.389

# Fidelity
cat data/eval/fidelity.json | jq .ks, .netsimile, .dcr, .pass, .elliptic_available
#  0.5 3.468 0.72  {"ks":false,"netsimile":true,"dcr":true}  true  -> ks false

# GNN stub
ls -lh models/gnn.pt; wc -c models/gnn.pt  # 73 B
grep -n "GCNConv.*38.*64" ml/train_gnn.py
grep -n "TORCH_BLAS_PREFER_HIPBLASLT" ml/train_gnn.py

# Trace stub
wc -c data/alerts/gnn_explain_cache.json | awk '{print $1/1024/1024 " MB"}'
python3 -c "import json; j=json.load(open('data/alerts/explanations.json')); print(j[0]['subgraph'], len(j))"
grep -n "get_gnn_subgraph" ml/explain.py

# Ingest dual-engine parity scaffold
grep -c "INGEST_ENGINE" README.md
ls -lh data/graph/nodes.parquet data/graph/edges.parquet 2>&1 | head

# 511 vs 234K narrative
python3 -c "import duckdb; c=duckdb.connect('data/graph/duck.db',read_only=True); print('edges', c.execute('SELECT count(*) FROM edges').fetchone()[0]); import pathlib; print('elliptic edgelist', sum(1 for _ in open('data/raw/elliptic/elliptic_txs_edgelist.csv'))-1)"
wc -l data/raw/elliptic/elliptic_txs_*.csv
du -sh data/raw/elliptic
```

---

*No metric invented. Every `pr_auc`, `ece`, `ks`, edge count, `n_unique`, and byte-size above is `cat`/`wc`/`du`/`parquet` on this checkout. Synthetic success does not imply real success — re-run on `elliptic_txs_classes.csv` before deploying.*
