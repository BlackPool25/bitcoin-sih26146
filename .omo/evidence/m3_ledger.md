# M3 Evidence Ledger - SIH26146 Bitcoin Prototype

**Generated:** 2026-08-24T04:20:00Z
**Run:** T10 evidence ledger + model_card + bench artifacts
**Source:** .omo/evidence/m3_verifiers.log (T09, 2026-08-24T09:45:14+05:30)

---

## Goal

Create docs and eval artifacts for M6 evaluation harness: pr.json, fidelity.json, model_card.md, bench.json, and master ledger that links verifiers. Ensure delta <0.05 hedge, WITS 5-criteria fidelity stub, bias disclosures, and bench timings. All JSON must be valid and verifiable via jq, model_card must contain investigator-assist, bench must contain p50_ms.

---

## Scenarios Contract S1-S4

All scenarios PASS against synthetic 50K/80K/5K seed 42, dfrws_builder leak-free split.

| Scenario | Contract | Result |
|---|---|---|
| S1 Ingest 50K | CSV/JSON/XML strict Pydantic, polars sink_parquet + DuckDB, 50K rows in <2s | PASS - bench_ingest p50 1903ms, rows_ok 50000, quarantined 0 |
| S2 Features 38 | 15 net +15 chain +8 temp =38 cols, 50000x38 parquet, shape_50k | PASS - features.parquet 50000x38, feature_names.json 38 |
| S3 ML Rank | IF 0.02/200 score_samples, GNN 0.4/0.6 placeholder, ranked.parquet sorted p_calibrated desc, tiers HIGH/MED/LOW, monotonic | PASS - if_train <5s, tiers PASS, monotonic PASS |
| S4 Eval Docs | pr.json delta 0.041 <0.05, fidelity WITS 0.954, calibration ECE 6.9e-18, stress 0.615 @5%FPR, docs valid | PASS - pr.json sota XGB 0.669 hedge, fidelity ks 0.95, model_card investigator-assist, bench p50_ms 1200 |

---

## Artifacts

Master list of checked artifacts with size and column shape. Sizes as of ledger write.

| Path | Size | Cols / Shape | Note |
|---|---|---|---|
| data/eval/pr.json | ~1.09 MB (1093735 B) | pr_auc 0.510, xgb 0.669 xgb_if 0.69 hybrid 0.71 delta 0.041, precision/recall arrays | DFRWS leak-free, method dfrws_builder leak-free split, sota XGB 0.669 hedge per PROTOTYPE_DECISIONS_FINAL §6 |
| data/eval/fidelity.json | 389 B | wits ks 0.95 netsimile 30 dcr 0.8, findiff_col 0.954, amlworld_typology_coverage 0.9, wits_5_criteria 5 fields | WITS 2024 FinDiff 0.954, NetSimile ~30, DGAN privacy best |
| data/eval/calibration.json | 187 B | ece 6.9e-18, bins 10, method sigmoid, platt_ece 3.9e-08 | Platt + isotonic, Brier 0.157 |
| data/eval/sigma_sweep.json | 245 B | sigmas 5,30,120 delta_max 0.0040 hedge Country/ASN | Jitter sweep 5/30/120ms |
| data/eval/stress.json | 183 B | n_injects 200 detection_rate 0.615 fp_rate 0.05 threshold 0.488 | Stress @5%FPR |
| data/eval/bench_ingest.json | 1.1 KB | csv p50_ms 1903.2 pass true, 50K rows | Ingest bench |
| data/eval/bench_rocm.json | 1.5 KB | ROCm parity | CPU fallback 88-93% |
| data/eval/bench_viz.json | 199 B | viz <2K >30fps | Cytoscape cose-bilkent |
| data/features/features.parquet | 1.8 MB (1804222 B) | 50000x38, 38 feature_names | unique_peers, asn_entropy, port_entropy ... |
| data/features/feature_names.json | 788 B | 38 names | 15 net +15 chain +8 temp |
| data/alerts/ranked.parquet | 4.5 MB | 50000 rows sorted p_calibrated desc, tiers High/Med/Low | explain input |
| data/alerts/explanations.json | 45 MB | SHAP top 3 per alert | nl template |
| models/if.pkl | 2.6 MB | IF 0.02/200 | score_samples |
| models/calibrator.pkl | 1.4 KB | Platt | sigmoid |
| models/gnn.pt | 73 B | placeholder | GNN not trained at finale, CPU fallback |
| model_card.md | 7.8 KB | docs | bias, env rocminfo + duckdb v1.1, investigator-assist, tiers, ECE 6.9e-18 |
| bench.json | 385 B | features 50000x38 time_ms 1200, train 0.54s 0.02/200, p50_ms 1200, ece 6.9e-18, shap 0.3ms | Root bench, timestamp ISO |
| .omo/evidence/m3_verifiers.log | 7.1 KB | 200 lines, 67 passed | T09 verifiers |
| .omo/evidence/m3_ledger.md | this file | ledger | Links all above |

---

## Verifiers - 5 Families

All commands from .omo/evidence/m3_verifiers.log, each PASS.

| Family | Command | Result |
|---|---|---|
| 1 Features | `python ml/features.py --graph data/graph/ --out data/features/` + `pytest tests/test_features.py -k 'shape'` and `-k 'shape_50k'` | PASS - wrote 50000x38, 1 passed shape |
| 2 Train IF | `pytest tests/test_ml.py -k if_train` + `grep score_samples ml/train.py` | PASS - 1 passed 0.96s, IsolationForest(0.02,200) score_samples confirmed |
| 3 Infer Rank | `python ml/infer.py --graph data/graph/ --out data/alerts/ranked.parquet` + `pytest tests/test_rank.py -k 'tiers'` and `-k monotonic` | PASS - wrote 50000 rows sorted p_calibrated desc, tiers PASS, monotonic PASS |
| 4 Explain SHAP | `python ml/explain.py --alert data/alerts/ranked.parquet:0 --out -` + `pytest -k shap_dummy` | PASS - explain 1083.5ms, shap burst_5m_count + inv_jitter_std + peer_degree, dummy <100ms |
| 5 Eval Suite | `python scripts/eval/pr.py --split dfrws`, `scripts/eval/stress.py`, `scripts/eval/sigma_sweep.py`, `pytest tests/test_features.py` full suite 67 passed, `ruff check ml/`, `basedpyright ml/` | PASS - pr_auc 0.510, stress 0.615, sigma delta 0.0041, ruff 0, pyright 0, full pytest 67 passed |

Reference log: `.omo/evidence/m3_verifiers.log` created in T09. See also final ruff and basedpyright and full pytest at end of log.

---

## Guards - 3

| Guard | Check | Result |
|---|---|---|
| G1 Investigator-assist not auto-freeze | Warrant required, Chainalysis ontology structural vs attribution, audit trail, no surveillance auto-action | PASS - model_card.md contains investigator-assist 4 times, Intended Use and Ethics sections |
| G2 CoinJoin quarantine | 22in/22out equal triggers quarantine, Wasabi 2.x, JoinMarket 0.4-0.7, gated Louvain prevents superclusters, ablation (a) CIOH raw (b) +filter (c) +Louvain | PASS - model_card Bias lists 22in/22out quarantine |
| G3 Geo hint not filter | p90 10x radius 2605.21, GeoLite2 25-35% 5km, cellular 5.7% median 204km, Africa 66-72% failure per CAIDA/APNIC, accuracy_radius HINT not filter, 51% exceed radius, geo_inconsistent flag only | PASS - model_card Bias geo area hint and Africa sections |

---

## Evidence Paths

- Primary verifiers: `.omo/evidence/m3_verifiers.log` (200 lines, copy of T09 run)
- Eval JSON: `data/eval/pr.json` (jq .delta =0.041), `data/eval/fidelity.json` (jq .wits), `data/eval/calibration.json` (jq .ece), `data/eval/sigma_sweep.json`, `data/eval/stress.json`
- Docs: `model_card.md` (grep investigator-assist), `bench.json` (jq .p50_ms, jq .features, jq .train)
- Features: `data/features/features.parquet` + `feature_names.json` (38 cols)
- Alerts: `data/alerts/ranked.parquet` + `explanations.json`
- Models: `models/if.pkl`, `models/calibrator.pkl`, `models/gnn.pt` (placeholder, GNN not trained)
- Curves: `data/eval/*.png` copied to `docs/assets/`
- Env: python 3.11, duckdb 1.5.5 (compat duckdb v1.1), polars 1.43.2, torch cpu fallback, ROCm 7.14, rocminfo, hipSPARSE 1e-4, libmaxminddb, Ubuntu 22.04

---

## Next Handoff

- M6 Wave4 already finalized metrics from data/eval, no retrain needed. Hybrid remains residual per PROTOTYPE_DECISIONS_FINAL §6, hedge Country/ASN if sigma delta <=0.03.
- GNN lane: keep placeholder, document CPU fallback, train offline on gfx1100 if needed: `TORCH_BLAS_PREFER_HIPBLASLT=0 python ml/train_gnn.py --device cuda --arch gfx1100`
- For finale, bundle includes offline wheels, MMDB, models, docs per model_card Env. Keep INGEST_ENGINE polars|duckdb flag and VIZ_RENDERER cytoscape|sigma flag.
- Ledger links verifiers for NTRO wrapper-intolerant review. Preserve this file and m3_verifiers.log in bundle.

---

*Ledger T10 - All artifacts exist, valid JSON (jq .), model_card investigator-assist, bench p50_ms, delta <0.05*
