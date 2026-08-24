# SIH26146 — AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic — Decision-Complete Prototype Record

**Date:** 2026-08-23 · **Author:** Sisyphus (Muse Spark) + Shreyas Team  
**Mode:** ULTRAWORK · **Research Dir:** `/home/shreyas/Downloads/OmniLearn/.omnilearn/research/sih26146-bitcoin-transaction-traffic/`  
**Problem Statement:** SIH26146 — National Technical Research Organisation (NTRO) · Software · Transportation & Logistics (mislabeled, domain is Blockchain & Cyber) · **75 PASS FRESH** Rank 1/2 (75/75 tie) · 0/500 submitted · Deadline 20 Sep 2026  
**This file:** Every option discussed across 28 Q&As + the decision taken on each + the explicit 9+1 architecture that combines into the solution. All future agents build from this file alone.

---

## §0 Problem Statement — What NTRO Actually Wants (Verified)

**Verbatim objective (CSV row s_no 146, SIH26146, python csv.DictReader 2026-08-21, confidence 92%):**

> Background: Bitcoin's pseudonymous, peer-to-peer design lets criminal actors move, layer, and cash out illicit funds — ransomware payments, darknet-market proceeds, extortion, and laundering — while evading traditional financial surveillance.
> Objective: design and build a **complete offline system for Linux** that ingests bulk Bitcoin transaction/network metadata (CSV/JSON/XML), **correlates network-layer (IP/port/timing) observations with blockchain-layer (wallet/TXID/amount) data**, and applies **AI/ML to detect anomalies, cluster entities, and generate prioritized, explainable investigative leads**.

**5 Challenge Objectives:**
1. Ingest & parse bulk metadata dataset (`timestamp, src_ip, dst_ip, src_port, dst_port, txid, input_addresses[], output_addresses[], input_amounts[], output_amounts[], fee, script_type`) — formats CSV/JSON/XML
2. Build an **entity/transaction graph** linking IPs ↔ wallets ↔ transactions
3. Implement **AI/ML detection use case** (Section-4 table in full PDF, not in CSV — unknown beyond excerpt) with a **working model — not just rules**
4. Generate a **ranked, explainable alert list** (why flagged + confidence score)
5. Present via **simple dashboard or link-analysis visualization**

**Dataset Spec:** Synthetic dataset modelled on real Bitcoin P2P/transaction fields — **no real seized or live-intercept data provided**. Minimum fields as above + `geo_country/asn` (integrate open-source downloadable GeoIP database — e.g., MaxMind GeoLite2). Format CSV/JSON/XML.

**Expected Solution (4):** workable offline Linux prototype (code repo) with ingestion + correlation + AI/ML model; short technical write-up (approach, model choice, explainability); dashboard/visualization showing flagged entities and evidence per flag.

**Scoring snapshot (ranked-initial.csv, 155-real pool, base 50 + org 10 + data 1 + demo 6 + team 6 + novelty 2):**
- SIH26146 Rank 1/75 PASS FRESH, data 1, demo 6, team 6, org 10 (NTRO HIGH 70-80%), already-built 0, flag 0, competition 0 (Transportation 7/155 = 4.5% — 2nd-least crowded vs Disaster 23/Smart Automation 24/Blockchain 20)
- Researcher viability 8.2-8.5/10 — PICK NOW (Top-2, best NTRO data+cyber pair)
- NTRO context: 23 PS total (22 Software +1 misc), 2nd-largest org after MoES 30, **13 winners 2024 verified** at `sih.gov.in/sih2024/sih2024-grand-finale-result` + MIC Report p3-4, wrapper-intolerant judges (HITK overnight SAR pivot precedent), MEDIUM already-built (no public NTRO Bitcoin portal to clone)
- Dataset_link `""` empty — not a blocker (Elliptic 203k/234k, GeoLite2 MMDB 68MB, mempool.space/Esplora APIs abundant)
- Freshness: FRESH cohort 79/155 (51%) — only near-match SIH260378 (2024, J=0.125, 1 token, fails threshold), no prior "Bitcoin Transaction Traffic" PS, GitHub SIH26146 0 hits (85% no replica)
- 36h demoability: 8.5/10 — 28-32h critical path, offline bundleable (synthetic + MMDB + pre-fetched samples)

**Unknowns flagged:** Full PDF Section-4 AI/ML focus table not in CSV; whether NTRO distributes synthetic CSV before finale (team must assume generate); judge crypto-depth expectation (peel/mixer/CoinJoin glossary needed).

---

## §1 Architecture — 9+1 Interlocking Parts (User Confirmed: 9-part good + Evaluation harness really important + UX very important)

```
               ┌──────────────────────────────┐
               │ 2. Synthetic Gen (Elliptic- │ ┐
               │    anchored 50K/80K/5K)      │ │  3. GeoIP/ASN (GeoLite2 68MB)
               └──────────────────────────────┘ │  ┌──────────────────────┐
                                                ├──►│1. Ingest & Normalize │
               ┌──────────────────────────────┐  │  │ Pydantic strict,     │
               │ 3. GeoIP Enrichment          │──┤  │ polars/ijson/lxml    │
               │                              │  │  │ CSV/JSON/XML + poll  │
               └──────────────────────────────┘  │  │+WS+replay            │
                                              │  └───────────┬──────────┘
                                              │              │
                                              │              ▼
                                              │  ┌───────────────────────────┐
                                              │  │4. Multi-layer Graph      │
                                              │  │ DuckDB+DuckDB+NetworkX   │
                                              │  │ IP↔TXID + UTXO + temporal│
                                              │  │ + ASN community (Louvain) │
                                              │  └────────────┬──────────────┘
                                              │               │
                                              └──────────────►├────────► 5. Features 40/40/20 (38)
                                                                       │  (15 net +15 chain+8 temp)
                                                                       ▼
                                                          ┌─────────────────────────┐
                                                          │6. Hybrid ML            │
                                                          │ IF+LOF (seconds) + GNN │
                                                          │ PyG ROCm AMD 7900GRE   │
                                                          │ weighted ensemble 0.4/0.6│
                                                          └────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                          ┌─────────────────────────┐
                                                          │7. Rank/Conf/Explain    │
                                                          │ Platt+isotonic p, tiers │
                                                          │ SHAP top-3 + NL template │
                                                          └────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                          ┌─────────────────────────┐
                                                          │8. Dashboard            │
                                                          │ Cytoscape.js alert-first│
                                                          │ React+Vite+Recharts    │
                                                          │ table → subgraph drill │
                                                          └────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                          ┌─────────────────────────┐
                                                          │9. Offline Packaging    │
                                                          │ Docker Compose <3min   │
                                                          │ wheels+MMDB+weights USB│
                                                          └────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                          ┌─────────────────────────┐
                                                          │10. Eval Harness+Writeup│
                                                          │ Elliptic PR + synth    │
                                                          │ stress + judge inject  │
                                                          │ PDF+notebook+model card│
                                                          └─────────────────────────┘
```

**Parts 0 (meta):** Hedge — submit early 1-5 Sep, monitor `submitted_count` 09:00/18:00 via DataTables payload `sih.gov.in/sih2026PS`, reserve SIH26182; Gate — air-gapped `docker compose up` <3min on finale laptops (judges run code on their laptops per Sameer post).

---

## §2 Every Option Discussed & Decision Taken (28 Q&As)

### Q1 — PS Decomposition
| Option | Description |
|--------|-------------|
| A | 9-part as proposed (Ingest → Synthetic → GeoIP → Graph → Features → ML → Explain/Rank → Dashboard → Offline+Docs) — clean separation |
| B | Merge Graph+Features+ML into one Analytics Core |
| C | Split Dashboard into Alert List / Graph Viz / Evidence Drill-down (UX-first) |
| D | Add 10th: Ops (Evaluation Harness + Benchmarking) |

**Decision:** **9+1 — Keep 9 parts + Add 10th evaluation harness** (you: "9 part is good too and Evaluation harness and benchmarking is really important" + "UX very important"). Rationale: NX separation lets agents build in parallel without merge conflicts; harness is not optional for NTRO "working model" proof.

### Q2 — Team & Deadline
| A | 6-member SIH team, Sep 20 deadline — internal hackathon early Sep, finale Dec |
| B | 2-3 core builders only — prune to 28h |
| C | Solo/portfolio — proof-of-concept |
| D | Research-first, no deadline |

**Decision:** **A — 6-member SIH, Sep 20 deadline**. Implication: must optimize for wrapper-intolerant NTRO breadth + 36h air-gapped demo, not research novelty. All downstream sizing (28-32h critical path) anchored here.

### Q3 — Winning Intent
| A | WIN SIH — optimize for judge score |
| B | Learn Bitcoin forensics deeply |
| C | Portfolio / job signal |
| D | Paper / publication |

**Decision:** **A — WIN SIH**. Every decision weighted at rubric: org intent 25% + demo 15% + team 15% + already-built negative dominates. Novelty is 5% — execution breadth + thin angle (IP↔chain + SHAP) wins over SOTA chasing.

### Q4 — Data Strategy (EMPTY dataset_link)
| A | Pure synthetic (faker+random) |
| B | **Elliptic-anchored synthetic** |
| C | Live API seeded + synthetic |
| D | Wait for NTRO dump |

**Decision:** **B — Elliptic-anchored synthetic** (you). Real Elliptic txs (203k, 4,545 illicit, 49 timesteps, 234k edges) as chain-layer ground truth + synthetic P2P layer (IP/port/timing Gaussian jitter). Rationale: satisfies "no real seized data" spec, gives leakage-aware eval baseline (DFRWS 2026), judge-legible. Scales: see Q12.

### Q5 — Offline Constraint
| A | **Air-gapped finale laptops** |
| B | Offline-capable but online ok |
| C | Cloud demo fine |
| D | Hybrid offline+live |

**Decision:** **A — Air-gapped** (you). Bundle 68MB MMDB + model weights (≈50MB GNN +1MB IF pickle) + 50K synthetic CSV + node_modules + wheels on USB. Docs: judges run code on their laptops via Docker (Sameer 36h post) — if it doesn't run offline, teams called separately to fix; non-deterministic live API = death.

### Q6 — Tech Stack
| A | **Python + FastAPI + React** |
| B | Next.js full-stack + Py microservice |
| C | Go/Rust backend + Python ML |
| D | All-in Python Streamlit/Dash |

**Decision:** **A — Python + FastAPI + React** (you). Fastest SIH velocity: Polars/Pydantic/DuckDB backend, NetworkX graph, sklearn/shap, React+Vite+shadcn+Cytoscape/Recharts. Next.js split adds 2-service ops overhead; Go overkill; Streamlit under-polished for NTRO.

### Q7 — Graph Depth (THE thin angle)
| A | Simple bipartite IP↔TXID↔wallet |
| B | Temporal correlation (P2P timing) |
| C | Full UTXO graph + clustering heuristics |
| D | **Multi-layer: network + UTXO + temporal + ASN community** |

**Decision:** **D — Multi-layer** (you). Network (IP↔TXID via P2P/ASN co-occurrence) + UTXO (wallet↔TXID via inputs/outputs, CIOH gated) + Temporal (bursts/communities) + Community (Louvain on ASN+wallet). DuckDB OLAP + NetworkX DiGraph (50K scale, Neo4j +400MB rejected). This is the differentiator vs "just run GNN on Elliptic".

### Q8 — ML Model (Not Just Rules Probe)
| A | IsolationForest+LOF on 38 handcrafted feats (seconds, SHAP-ready) |
| B | Pre-trained GNN on Elliptic (GCN/GAT via PyG, inference only) |
| C | **Hybrid: IF + GNN ensemble** |
| D | Hosted LLM/BERT on tx sequences |

**Decision:** **C — Hybrid IF+GNN ensemble** + **AMD ROCm HIP** (you: "Hybrid but also keep in mind I have AMD 7900GRE ensure AMD compatible"). Weighted ensemble IF 0.4 + GNN 0.6 → raw score; trains in seconds (IF) + load weights (GNN) → no training wall at finale. AMD 7900GRE = gfx1100 Navi 31 — needs ROCm 7.14 PyTorch + `torch[device-gfx1100]` + community `pyg-rocm-build` (PyG official ROCm wheels NOT on data.pyg.org). Fallback: train offline on AMD at home, demo 100% CPU for determinism (your final choice pending in Q15).

### Q9 — Explainability (SCORED)
| A | **SHAP per-alert + NL template** |
| B | Full SHAP waterfall + graph snippet |
| C | Rule-based explanation only |
| D | LLM narrative via local phi-3/ollama |

**Decision:** **A — SHAP per-alert + NL template** (you). "Wallet 1A… flagged: 12 outputs <1 BTC in 8 min, peers RU/CN — conf 0.87 (fan-out + geo hop + burst)" — SHAP top-3 → Jinja. B is stretch if buffer; C risks "just rules" fail; D non-deterministic + heavy bundle.

### Q10 — Feature Scope (36h trade)
| A | Network-layer heavy |
| B | Chain-layer heavy |
| C | **Balanced 40/40/20** |
| D | Minimal MVP 15 feats |

**Decision:** **C — Balanced 40/40/20** (you). Network 15 (peers, ASN/port entropy, geo variance, inv jitter) + Chain 15 (fan-in/out, amount var, fee sat/vB, script hist, input cnt) + Temporal 8 (burst counts, inter-TX std, modularity delta). SHAP will rank; breadth signal beats narrow. Minimal MVP safe but less impressive.

### Q11 — Visualization Fidelity (5-min judge window)
| A | **Cytoscape.js link-analysis + alert table** |
| B | D3-force custom + geomap + timelines |
| C | vis-network / Sigma.js |
| D | Dashboard-first table + modal drill-down |

**Decision:** **A — Cytoscape.js + alert table** (you). Industry standard, `cose-bilkent` layout, canvas renderer, edges>nodes cost — paging for 50K. D is the workflow variant inside A; see Q13.

### Q12 — Synthetic Scale
| A | 10K/15K/1K IPs — toy fast |
| B | **50K txs / 80K edges / 5K IPs** |
| C | 200K full Elliptic + synthetic P2P |
| D | Param slider (1K/10K/50K) |

**Decision:** **B primary + D as stretch** (you). Medium realistic: <2s load, cytoscape smooth, scalability narrative. D (judge slider) is ideal if time — demonstrates engineering breadth; 10K too toy, 200K needs pagination.

### Q13 — Alert Ranking Calibration (NTRO probes)
| A | Raw model score 0-1 |
| B | **Platt-scaled + isotonic** |
| C | Risk tier Crit/High/Med/Low |
| D | Conformal intervals |

**Decision:** **B — Platt-scaled + isotonic** (you) → calibrated p ∈[0,1], tiers Crit>0.9 / High 0.75-0.9 / Med 0.5-0.75 / Low <0.5 (from Q14). Proper confidence, calibration curve shown. A simple but not credible; D rigorous but heavy to explain in 5 min.

### Q14 — Offline Bundle Strategy
| A | Bundle everything: MMDB+weights+CSV |
| B | Generate synthetic live at demo |
| C | Pre-fetch real samples + synthetic overlay |
| D | **Docker Compose one-click offline** |

**Decision:** **D — Docker Compose one-click** (you, subsumes A). `docker compose up` → FastAPI :8000 + React :5173 + DuckDB file, cold-start <3min, healthcheck. Wheels + MMDB + CSV + node_modules on USB, Ubuntu 22.04 LTS baseline, ROCm fallback to CPU if driver missing.

### Q15 — AMD GPU (7900 GRE gfx1100)
| A | **ROCm + PyTorch + PyG HIP** |
| B | CPU-only training, AMD inference |
| C | ONNX Runtime + DirectML |
| D | Avoid GPU at demo — CPU determinism |

**Decision:** **A — ROCm HIP** (you) with fallback D implicitly approved. ROCm 7.14 + `torch[device-gfx1100]` + TORCH_BLAS_PREFER_HIPBLASLT=1 (fix Navi31 perf <2.14) + `pyg-rocm-build` community wheels for `torch_scatter/sparse/cluster`. Build offline on AMD at home; demo CPU fallback if finale laptop lacks ROCm. ONNX (C) is lighter alternative if ROCm bundling fails — research will compare.

### Q16 — Ingest Format Strictness
| A | **Pydantic strict + streaming (polars/ijson)** |
| B | Pandas lenient + coercion |
| C | Multi-format auto-detect + validation report |
| D | CSV-only MVP |

**Decision:** **A — Pydantic strict + streaming** (you) — `Model.model_validate(strict=True)`, streaming 100K-row chunks, per-file validation report quarantining error rows. C is the stretch inside A (auto-detect CSV vs JSON vs XML); D risks judges testing JSON. Production-quality signal to wrapper-intolerant NTRO.

### Q17 — Graph Storage (50K scale)
| A | NetworkX in-memory + pickle |
| B | Neo4j Docker (+400MB) |
| C | SQLite adjacency tables |
| D | **DuckDB + graph in Python** |

**Decision:** **D — DuckDB + Python** (you). Nodes/edges tables + indices in DuckDB file (Parquet polyglot via `read_csv_auto`, `read_json_auto`, `COPY`), NetworkX DiGraph for Louvain/betweenness. DuckDB small bundle, OLAP fast, no 400MB Neo4j tax; in-memory alone (A) loses SQL join power for geo+wallet correlation.

### Q18 — Temporal Correlation Credibility
| A | **Synthetic inv timing with Gaussian jitter** |
| B | Reuse real mempool timing samples |
| C | SimPy discrete event simulation |
| D | Skip timing, focus topo+geo |

**Decision:** **A — Gaussian jitter** (you). `inv_ts = tx_broadcast ± N(0,30s)` per peer — plausible story: "P2P inv messages observed at nodes X/Y correlate to TXID Z broadcast timing". B is the pre-fetch enhancement (mempool.space first-seen timestamps) on top of A if time; C defensible but heavy; D weakens thin angle.

### Q19 — Anomaly Types (NTRO threat model)
| A | Classic: peel, mixing, fan-out, structuring |
| B | Advanced: CoinJoin, bridge layering, high-fee |
| C | Network-anomalous: ASN hopping, port scan |
| D | **All of above — ranked by risk tier** |

**Decision:** **D — All ranked by risk** (you). Synthetic injects: peel (1-in-2-out seq), mixer fan-in/out, CoinJoin (Wasabi/JoinMarket), structuring (<1 BTC), ransomware burst, cross-chain bridge layering, high-fee laundering, ASN hopping. Ranked Crit→Low via calibrated p + risk tier. Maximal breadth; generator complexity ↑ but agent-parallelizable.

### Q20 — Benchmarking (Proof of Working Model)
| A | Hold-out Elliptic illicit labels + PR curve |
| B | Synthetic ground-truth injection + detection rate |
| C | **Both: Elliptic PR + synthetic stress** |
| D | Live judge injection at demo |

**Decision:** **C — Both** (you) + D as interactive spice (Q13's judge injection). Track A: 70/30 split → PR-AUC, FPR@90%TPR vs rule baseline (XGBCLUS). Track B: 200 known illicit injects → detection rate + FP. Metrics dashboard: PR curve + calibration curve + SHAP summary. D: "Inject peel chain" button → live alert (proof of learning).

### Q21 — Write-up (Expected Solution)
| A | 6-page PDF + mermaid |
| B | Jupyter notebook |
| C | **Both: PDF + notebook + model card** |
| D | Minimal README |

**Decision:** **C — PDF + notebook + model card** (you). PDF for judges (problem→arch→features→model→explain→eval→offline), notebook executable (ingest→graph→ML→SHAP cells judges can run), model card (bias: CoinJoin FP, geo accuracy radius caveat 25-35% ≤5km free tier, warrant note: "investigator-assist not auto-freeze"). Minimal README looks thin to NTRO.

### Q22 — UX Workflow Deep Dive
| A | **Alert-first: ranked list → click → graph drill-down** |
| B | Graph-first: full network → lasso → alerts |
| C | Split-pane: list left, graph right synched |
| D | Story-mode walkthrough |

**Decision:** **A — Alert-first** (you). Landing = ranked table (0.95→0.52), click → cytoscape subgraph + evidence panel (geo timeline, amount flow, SHAP waterfall). Fastest triage in 5-min window; C is persistent split variant if layout buffer; D is guided narrative stretch for finale rehearsal; B heavy render at 50K.

### Q23 — Real-time vs Batch Ingest
| A | Batch only |
| B | Batch + streaming mock (polling) |
| C | Batch + live WS if online |
| D | **All three: batch + poll + WS + replay** |

**Decision:** **D — All three + replay** (you). Batch primary (spec) + folder-watch poll (30s auto-ingest) + optional mempool.space WS (doc'd REST 429/Retry-After, ~10/s practitioner, track-mempool) via FastAPI mock offline, + time-slider replay. Graceful degradation story: core offline, live enrichment optional. Mirrors Chainalysis self-hosted advice — warm cache online, serve fixtures offline.

### Q24 — Team Ownership (6 members, agent-buildable without conflicts — your constraint)
| A | 2 ingest/graph +1 ML +2 viz +1 integration (rec.md §3) |
| B | 3 vertical slices (peel/mixer/fan-out end-to-end) |
| C | Platform (3) + ML (2) + UX (1) |
| D | You tell me — propose optimal agent split |

**Decision:** **You: "I will be majorly building stuff but divide it into members such that I can have different agents build different parts correctly without causing issues"** → **Agent-Buildable Partition (special hybrid of A+C with interface contracts).** This is why Parts 1-10 have explicit file ownership + API contracts (see §3). You remain lead integrator; agents own bounded parts with frozen I/O schemas.

### Q25 — Privacy & Ethics Framing
| A | **Investigator-assist, not auto-freeze** |
| B | Full privacy-preserving framing |
| C | Performance-only, skip ethics |
| D | Include bias/warrant in model card |

**Decision:** **A — Investigator-assist** (you) + **D implied** (model card bias per Q21). Chainalysis ontology: structural/deterministic vs attribution — use graph steps as leads, human warrant required. Document CoinJoin FP bias + geo radius caveat; audit trail required. NTRO is intelligence org — surveillance framing not penalized but maturity signal = model card bias note.

### Q26 — Competition Hedge
| A | **Submit early 1-5 Sep, monitor cap** |
| B | Submit NTRO pair (26146+26163) |
| C | Cross-org hedge (26146 + MPLAD/OIL) |
| D | Ignore herd |

**Decision:** **A — Early Sep + cap monitor** (you). `submitted_count` 0/500 null at selection; monitor 09:00/18:00 from early Sep, alert ≥300 crowded / ≥450 risk / =500 FROZEN. B (NTRO×2) and C (cross-org) remain valid reserve strategies per `recommendations.md §2` if cap hits; but early submit beats herd.

### Q27 — Stretch Feature (Buffer After MVP)
| A | **Mixer/bridge typing (Wasabi/Tornado/RSK)** |
| B | Entity resolution (CIOH+change clustering → entities) |
| C | Temporal replay + geo animation |
| D | NL investigation assistant (LLM over DuckDB) |

**Decision:** **A — Mixer/bridge typing** (you). Classify mixing vs bridge vs peel — type-aware alerts, hardest forensics signal; aligns with Kappos 89.2% RF vs 87.5% rule, JoinDetect ML>heuristic. B is actually required MVP (CIOH gating), C/D are second-tier stretches (replay slider already in D, but animation polish if buffer).

### Q28 — Success Metric (Zero Tolerance Contract)
| A | Air-gapped docker compose up <3min + 5-min rehearsal PASS |
| B | Elliptic PR-AUC >0.85 + synthetic detection >90% @ <5% FPR |
| C | 3 external mentors say "not a wrapper" |
| D | **All three — no excuses** |

**Decision:** **D — All three must PASS** (you). Gate 1: offline cold-start + judge walkthrough in 5 min. Gate 2: quantitative — ML beats rule baseline on both tracks (PR-AUC, FPR@90%TPR, stress detection). Gate 3: qualitative wrapper test — source-assisted (TS file+line) + SHAP + graph breadth vs wrapper dashboard. Zero tolerance per ULTRAWORK.

---

## §3 Agent-Buildable 6-Member Partition (No Conflicts)

**You lead integration; each agent owns a bounded part with frozen I/O schema and no shared mutable files.**

| Member | Owns (Parts) | Deliverable | I/O Contract | Depends On | Parallel Group |
|--------|--------------|-------------|--------------|------------|----------------|
| **You (Lead)** | 10 Eval+Writeup + 9 Offline | `docker-compose.yml`, `model_card.md`, PDF, notebook, USB bundle | Owns `docker-compose.yml` only — others PR to you | 1-8 | Wave 3 |
| **M1 — Backend Ingest** | Part 1 (+2 synthetic gen assist) | `backend/ingest/` (Pydantic models, polars/ijson/lxml streams), `backend/api/ingest.py` (FastAPI upload + validation report) | Reads `data/raw/*.csv/json/xml` → writes `data/clean/parquet/*.parquet` + `data/reports/validation.json` — no one else writes those | — | Wave 1 |
| **M2 — Graph + Geo** | Parts 3+4 | `backend/graph/` (GeoLite2 enricher, DuckDB nodes/edges, NetworkX multi-layer, Louvain) | Reads `data/clean/parquet/*` + `GeoLite2-City.mmdb` → writes `data/graph/nodes.parquet`, `edges.parquet`, `duck.db` → read-only for ML/Viz | M1 | Wave 1-2 |
| **M3 — ML Core** | Parts 5+6+7 (features+hybrid ML+calibrate) | `ml/features.py`, `ml/train.py` (IF+GNN ensemble), `ml/calibrate.py` (Platt+isotonic), `ml/explain.py` (SHAP) | Reads `data/graph/*` → writes `models/if.pkl`, `models/gnn.pt`, `models/calibrator.pkl`, `data/alerts/parquet/*` (ranked+explained) — Viz reads only | M2 | Wave 2 |
| **M4 — Viz A** | Part 8 — Alert Table + Evidence Panel | `frontend/src/components/AlertTable.*`, `EvidencePanel.*`, `frontend/src/api/*` | Reads `GET /api/alerts` + `GET /api/evidence/{txid}` — owns `AlertTable*`, no overlap with Viz B | M3 (mock data OK Wave1) | Wave 2 |
| **M5 — Viz B** | Part 8 — Cytoscape Graph + Leaflet Geo + Replay | `frontend/src/components/GraphView.*`, `GeoMap.*`, `ReplaySlider.*`, `frontend/src/cytoscape/*` | Reads `GET /api/graph/{alert_id}` → renders subgraph — owns `GraphView*`, `GeoMap*` | M3 (mock data) + M4 (API shape) | Wave 2 |
| **M6 — Platform + Docs Assist** | Parts 9 assist + 10 harness scripts | `scripts/build_wheels.sh`, `scripts/bundle.sh`, `scripts/eval/*` (PR curves, stress tests), `docs/` assets | Writes `scripts/*`, `data/eval/*` — never touches `backend/*` or `frontend/*` | All | Wave 3 |

**Merge rules:** No two agents write same file; API shape frozen in `openapi.yaml`; `duck.db` schema in `schema.sql` v1 locked; frontend-backend via FastAPI `/api/*` only; all eval writes to `data/eval/` not `data/alerts/`.

**Pre-event ramp (3 days, once):** M1+M2 PortSwigger SQL? (no — here: MaxMind geoipupdate + networkx + Polars), M3 Elliptic notebook `linovives/bitcoin-fraud-gnn` + sklearn IF/SHAP, M4/M5 cytoscape.js `cose-bilkent` perf tuning, M6 ROCm 7.14 `torch[device-gfx1100]` + `pyg-rocm-build` wheels.

---

## §4 Pending Research Decisions (To Be Resolved After 4-Phase Engine)

These are explicitly LEFT OPEN pending literature merge + hypothesis falsification + adversarial evidence. The final `PROTOTYPE_DECISIONS_FINAL.md` (post-synthesis) will lock them with confidence ranges.

| Pending | Current Lean | Falsification Criterion | Will Be Resolved By |
|---------|--------------|-------------------------|---------------------|
| Polars vs DuckDB `read_csv_auto` for 50K ingest | Polars streaming (faster) per industry L4 | Would flip if DuckDB ingests 50K >2× faster in benchmark | Industry source-table: DuckDB Performance Overview + Medium 2026 benchmark |
| Cytoscape vs Sigma.js vs vis-network at 50K edges | Cytoscape (community + layout) | Falsified if Sigma GPU renders 50K >3× faster without layout jank | Cytoscape `performance.md` + PkgPulse 2026 + issue #292/#239 |
| GNN (GCN/GAT) vs XGBoost PR-AUC on leakage-free split | Hybrid wins (ChronoWave 0.98) vs DFRWS leakage critique (XGB 0.669 > GCN 0.198) | Falsified if strict temporal split shows XGB ≫ GNN by 24%+ | DFRWS 2026 opacity critique + Revisiting-GNNs 2025 |
| ROCm PyG wheels stability on gfx1100 | Community `pyg-rocm-build` works (Looong01) | Falsified if `torch_scatter/sparse` fails to hipify on glibc 2.32+ | ROCm docs + PyG Discussions #6370/#5612 |
| GeoLite2 accuracy radius filtering | NOT filter — area not point (p90 10× radius) | Falsified if MaxMind L3 proves `accuracy_radius` safe filter | Shavitt 2011 + BigDataCloud 2026 + 2605.21937 |
| SHAP on GNN vs GNNExplainer | SHAP on IF + GNNExplainer on GNN separately | Falsified if SHAP on aggregated 166 Elliptic feats misleads (opacity) | XAI ensemble SciDirect + DFRWS 2026 |
| Synthetic fidelity metric | FinDiff best fidelity (KS 0.954) vs WITS 5-criteria | Choose after WITS benchmark (NetSimile ~30) | WITS 2024 + AMLworld NeurIPS 2023 |

---

## §5 Competition & Risk Register

- **Hedge:** Theft is Transportation-stealth (4.5% theme) vs NTRO HIGH; still 22 NTRO PS = intra-org crowding. Early Sep submit + daily cap scrape.
- **Already-built:** 0 — no public NTRO Bitcoin portal (vs MoRD -4/MHA-SACHET -4). Must still write "WHAT WE DO THAT LIVE PORTAL DOES NOT" paragraph per portal URL.
- **Wrapper test:** NTRO 22 high → quality-filtered 150-300 expect; breadth+SHAP+graph beats 10 bare forms (dashboard/chatbot/CNN) at -10. Need source file+line per finding analog (here: feature name + SHAP value + graph viz).
- **Data risk:** Empty dataset_link — mitigated by Elliptic+GeoLite2; MMDB 50-55MB actual (not 239MB CSV), bundle twice-weekly snapshot; `accuracy_radius` caveat in model card.
- **AMD risk:** ROCm not CUDA — have CPU fallback.

---

## §6 Files & Next Steps

- **This file:** `~/projects/sih26146-bitcoin-prototype-decisions/DECISIONS.md` — single source of truth for all agents.
- **Research in-flight:** Academic review done (19 sources, contradictions preserved), Industry review done (37 sources, ROCm/PyG/GeoLite2/Docker docs) — both 2026-08-23 verified. Merge → `literature-review.md` + `source-table.md` + `contradictions-map.md` next, then H1-H5 hypotheses, then adversarial evidence (supporting vs devil's advocate), then synthesis with confidence ranges.
- **Next write:** `PROTOTYPE_DECISIONS_FINAL.md` — locks §4 pending with numeric confidence, agent prompts per part, offline bundle manifest, eval thresholds (PR-AUC >? @ FPR), Docker healthcheck.
- **Air-gapped gate rehearsal:** `docker compose up` cold-start <3min, 50K→alerts <14h, report <6h — record log before Sep internal hackathon.

---

*Decision-complete for 28 Q&As. 7 pending resolved by research synthesis. ULTRAWORK continuation: Phase 1 merge → Phase 2 hypotheses → Phase 3 adversarial → Phase 4 synthesis → final decisions.*
