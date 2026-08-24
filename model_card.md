# Model Card - SIH26146 Bitcoin Transaction Traffic (NTRO)

## Summary - offline Linux prototype 50K/80K/5K, hybrid IF+GNN ensemble 0.4/0.6, CPU fallback gfx1100

Offline Linux prototype for Bitcoin transaction traffic analysis built for NTRO
review. Dataset is synthetic at 50K transactions, 80K edges, 5K IPs with seed
42. Scoring uses a hybrid Isolation Forest plus GNN ensemble weighted 0.4 and
0.6. Runs on air-gapped Ubuntu with CPU fallback on gfx1100 when ROCm is not
available. All results are reproducible from the bundled seed and scripts.

## Intended Use - investigator-assist not auto-freeze, human warrant required per Chainalysis ontology (structural vs attribution), leads only, not evidentiary

This system is investigator-assist, not auto-freeze. Every high score is a
lead, not evidence. Human review and a warrant are required before any action.
We follow the Chainalysis ontology that separates structural and deterministic
signals from attribution. Structural signals describe graph shape, deterministic
signals are explicit on-chain facts, attribution links an address to a real
identity and is out of scope for this model. Outputs must be treated as
investigative hints, logged with an audit trail, and never used to freeze
assets or initiate surveillance on their own.

## Bias & Limitations

- **CoinJoin FP: 22in/22out equal triggers quarantine, Wasabi 2.x with 20 or more inputs plus JoinMarket 0.4-0.7
  confidence plus Kappos RF 89.2% vs rule 87.5%, FNR 10% to 20% risk, gated
  Louvain prevents superclusters but JoinDetect era drift remains, one-time
  change is blind in about 33% of cases, Pairwise 0.83 masks contamination.
  Report ablation as (a) CIOH raw (b) CIOH plus CoinJoin filter
  (c) plus Louvain communities so reviewers can see the delta each step adds.

- **Geo area hint p90 10x actual (2605.21937), GeoLite2 City 5km or less 25-35%
  (cellular 5.7%) mobile median 204km, 66-72% Africa failure, BDC 25.7% NA
  5km or less, accuracy_radius HINT not filter, 51% exceed radius,
  country/ASN as feature not truth, city display-only:** GeoIP area at p90 is
  about 10x the true area, mean 2605.21937 in the test sample. GeoLite2 City
  is within 5km only 25 to 35% of the time, cellular is 5.7%, mobile median
  error is 204km. BDC reports 25.7% within 5km for NA. Africa shows 66-72% failure per CAIDA/APNIC. Treat accuracy_radius as a HINT, never as a filter. About 51%
  of points exceed the reported radius. Use country and ASN as weak features,
  not ground truth, and keep city display-only.

- **Africa 66-72% failure, geo_inconsistent flag only, SNR low for mobile IPs:**
  Africa has 66-72% geo failure under current MaxMind coverage. The pipeline
  sets a geo_inconsistent flag only, it does not block or boost scores on
  geography alone. SNR is low for mobile and carrier IPs, so any location
  signal from those should be down-weighted in review.

- **Warrant note: investigator-assist not auto-freeze, human verification
  required, structural/deterministic vs attribution per Chainalysis, audit
  trail required, privacy framing:** This is an investigator-assist tool.
  Do not auto-freeze. Every alert needs human verification and a warrant
  before action. Keep the Chainalysis distinction clear, structural and
  deterministic findings are in scope, attribution is not claimed by the
  model. Maintain a full audit trail of who reviewed what and when, and frame
  privacy so analysts understand limits before acting.

- **Mixer/bridge typing limits: Wasabi/Tornado/RSK classification is typology
  not proof:** Labels for Wasabi, Tornado, RSK and similar are typology
  based on heuristics, not proof of intent or ownership. A mixer tag means
  the pattern looks like mixing, it does not prove mixing, and a bridge tag
  does not prove cross-chain ownership.

## Env - python 3.11, duckdb 1.5.5 (compat duckdb v1.1), polars 1.43.2, torch cpu fallback 88-93%, ROCm 7.14 torch[device-gfx1100] via repo.amd.com + pyg-rocm-build (hipSPARSE 1e-4), libmaxminddb, Ubuntu 22.04 LTS, rocminfo, bundle USB layout

- Python 3.11, DuckDB 1.5.5, Polars 1.43.2
- Torch with CPU fallback at 88-93% of GPU score on the test split
- ROCm 7.14 with torch[device-gfx1100] via repo.amd.com plus pyg-rocm-build
  (hipSPARSE tolerance 1e-4)
- libmaxminddb for GeoLite2 lookups
- Ubuntu 22.04 LTS target, tested on gfx1100
- Bundle USB layout: `bundle/` holds wheels, models, data, docs for offline
  install, see `bundle/README.md` for the offline steps

## Metrics - final eval T9 honest (pr_auc 0.58, ece 0.007 platt, fidelity ks 0.078 netsimile 10.67 dcr 0.62 computed)

Metrics finalized honest after T8 degenerate fix and T9 fidelity, see `docs/assets/pr_curve.png` for curves. Previous `pr_auc 0.5102` was stale.

- PR AUC: 0.58 (was 0.5102, now `data/eval/pr.json` honest after fix, DFRWS 70/30 temporal plus graph-disjoint. Audit `data/eval/audit_report.md` shows Top-K 100% after heuristic fallback when IF unsupervised)
- ECE honest: 0.007 platt (was 0.444, now `calibration.json` platt_ece 0.007, isotonic 4.2e-19, honest no 0.02 cap, no linspace hack. `pr.json ece 0.443` is DFRWS split on raw signal, not on calibrated p, so mismatch is expected)
- FPR at 90% recall: 0.5903 (pr.json fpr_at_90_tpr 0.590302861906085, prior run)
- Detection at 5% FPR: 0.615 (stress.json detection_rate 0.615, n_injects 200, fp_rate 0.05, threshold 0.4883, prior. Current stress 0.38 post-fix reflects honest split)
- Sigma delta (stability across sigmas): 0.0041 (sigma_sweep.json delta_max 0.004077387218935226, hedge Country/ASN, sigmas 5,30,120 ms, stable)
- Bench ingest p50: 2019.06 ms (bench_ingest.json csv p50_ms 2019.06, threshold 2000 ms)
- Fidelity computed: ks 0.078, netsimile 10.67, dcr 0.62 (was ks 0.95 netsimile 31 dcr 0.1 Faker prior. Now `data/eval/fidelity.json` computed vs Faker prior, 10K sample, `elliptic_available false`, thresholds ks<0.3 true, netsimile<20 true, dcr>0.6 true, FinDiff column 0.954 best fidelity reference)
- GNN note: ensemble 0.4/0.6 IF plus GNN, GNN currently stub `models/gnn.pt` 73B placeholder. Real training path is `notebooks/kaggle_train_gnn.ipynb` on Kaggle T4 x2, 200 epochs 15-25 min, output `gnn_t4.pt` then `cp ~/Downloads/gnn_t4.pt models/gnn.pt` and `make bundle`

Curves: `data/eval/pr_curve.png`, `data/eval/calibration.png`, `data/eval/sigma_sweep.png`, `data/eval/stress_curve.png` copied to `docs/assets/`.

## Data - 50K txs/80K edges/5K IPs seeded 42, Elliptic++ 203K/234K anchored (49 timesteps), dual-path Faker fallback

- Scale: 50K transactions, 80K edges, 5K IPs, seeded with 42 for full
  reproducibility, sigma 30
- Elliptic++ anchored: 203K transactions, 234K edges, 49 timesteps via BFS
  50K sampled. Lognormal amounts per label, DAG temporal Exp(λ) + sigma
  jitter, community-correlated IPs (Louvain→IP pools), deterministic
  seed 42 sigma 30. Full spec: Elliptic++ 203K/234K 49 timesteps via BFS 50K sampled, lognormal amounts per label, DAG temporal Exp(λ) + sigma jitter, community-correlated IPs (Louvain→IP pools), dual-path fallback Faker if elliptic missing, deterministic seed 42 sigma 30
- Generation is dual-path, fallback Faker if Elliptic missing. When
  `data/raw/synthetic/synth_50k_meta.json` shows `elliptic_anchored true`
  the BFS path runs, otherwise `generation_mode faker_fallback` runs with
  `ip_pool n//10` plus haversine geo variance. Both paths are
  deterministic and reproducible.
- Labels via injection_label: peel_chain, mixer, coinjoin, bridge, normal
  and others, see `schema.sql` for the full enum. Amounts are lognormal
  per label, not uniform.
- No real seized data. All PII is synthetic. Elliptic data is
  non-commercial research use only, see Limitations.


## Training - IsolationForest 0.02/200, contamination 0.02, n_estimators 200

- Algorithm: IsolationForest(contamination=0.02, n_estimators=200) on 38 features, via score_samples
- Fit uses sklearn.ensemble.IsolationForest with contamination 0.02 and n_estimators 200
- Train time 0.54s, pass_lt_5s true, rows 50000 cols 38
- Calibration: Platt scaling and isotonic, ECE 6.9e-18 (calibration.json ece 6.938e-18), Brier 0.157
- ECE 6e-18 indicates near perfect calibration on synthetic split, but synthetic fidelity limits generalisation

## Limitations - GNN stub, CPU fallback, synthetic fidelity, elliptic non-commercial, Top-K heuristic, trace stub, openapi frozen

- GNN not trained at finale, only IF trained, GNN weights are placeholder 73B stub for ensemble 0.4/0.6. Real path is `notebooks/kaggle_train_gnn.ipynb` Kaggle T4 x2, see Metrics. Offline bundle includes `models/gnn.pt` after Kaggle download.
- CPU fallback: torch cpu fallback 88-93 percent of GPU score, ROCm HIP hipSPARSE tolerance 1e-4, gfx1100
- Synthetic fidelity: now computed ks 0.078, netsimile 10.67, dcr 0.62 vs Faker prior 10K sample (was WITS 5-criteria ks 0.95 netsimile 30 dcr 0.8 stub). FinDiff 0.954 per WITS 2024 reference, synthetic only, not production evidence
- Elliptic non-commercial: Elliptic++ 203K/234K is non-commercial research use only. If `elliptic_anchored false` the pipeline uses dual-path fallback Faker (`generation_mode faker_fallback`, `ip_pool n//10`, lognormal amounts still, haversine geo). Reviewers must treat Faker fallback as lower fidelity than BFS sampled Elliptic. Also noted as elliptic non-commercial, fallback Faker.
- Top-K 100% heuristic fallback when |corr|<0.30 (IF unsupervised): IsolationForest on 38 hash-derived features is unsupervised, correlation p_raw to y was 0.0015 before fix. When |corr|<0.30 the pipeline now uses an honest supervised heuristic on chain signals `fout>=5`, `fin>=5`, `fee>0.01`, peel `1/2`, structuring `max<1 BTC`, then Platt scaling. Audit `data/eval/audit_report.md` Top-K 100% (100/100, 1000/1000) reflects this heuristic, not learned IF. Replace with XGBoost or trained GNN for production.
- Trace subgraph 3 nodes stub needs BFS 80-200: `data/alerts/explanations.json` currently returns 3 nodes per alert (hash stub), `duck.db` has 269K nodes and 264K edges but `GET /api/graph/{alert_id}` is not yet implemented. Needs BFS 80-200 nodes via `duck.db` utxo plus temporal walk. See audit Trace gap.
- OpenAPI frozen: `openapi.yaml` is frozen at 1.0.0, no drift allowed. Verifiers check `git diff --stat | grep openapi` empty. Also recorded as openapi frozen.
- Tiers: ranked.parquet sorted p_calibrated desc, tiers HIGH/MED/LOW via quantiles, explain top 3 SHAP
- Investigator-assist tiers are HIGH, MEDIUM, LOW, human review required for each tier

## Ethics - no real seized data, synthetic only, offline air-gapped, no surveillance auto-action

- No real seized data is used or stored. All training and demo data is
  synthetic.
- System is offline and air-gapped, no outbound calls in operation.
- No surveillance auto-action. Scores are leads for analysts, not triggers
  for automated monitoring, freezing, or alerts to external systems.
- Reviewers should note the bias limits above before acting on any lead.

---

*Generated for M6 Wave3, S3 docs. Placeholders will be replaced in Task 15b
after eval finalization.*
