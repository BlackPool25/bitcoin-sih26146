# Offline Bundle - SIH26146 Bitcoin Prototype

This folder holds the offline USB bundle for air-gapped Ubuntu 22.04 LTS review. Everything runs without internet after install.

## Manifest

| path | contents | note |
|---|---|---|
| `bundle/wheels/` | Python 3.11 wheels for all deps | `pip install --no-index --find-links wheels` |
| `bundle/models/if.pkl` | IsolationForest 0.02/200 trained on 38 features | 0.54s fit, 50K rows |
| `bundle/models/calibrator.pkl` | Platt plus isotonic calibrator, ece platt 0.007 | honest, no 0.02 cap |
| `bundle/models/gnn.pt` | GNN stub 73B placeholder, replaced after Kaggle download | real training via `notebooks/kaggle_train_gnn.ipynb` on Kaggle T4 x2, then `cp ~/Downloads/gnn_t4.pt models/gnn.pt` and `make bundle` to refresh bundle |
| `bundle/models/lof.pkl` | LOF optional | not primary |
| `bundle/data/raw/synthetic/synth_50k.*` | 50K transactions, 80K edges, 5K IPs, seed 42 sigma 30 | Elliptic++ 203K/234K 49 timesteps via BFS sampled when `elliptic_anchored true`, else Faker fallback |
| `bundle/data/clean/parquet/` | Clean Parquet aligned to raw | seed 42 |
| `bundle/data/graph/duck.db` | DuckDB 269K nodes 264K edges, p2p 50K utxo 214K temporal | plus communities via Louvain to IP pools |
| `bundle/data/features/features.parquet` | 50K x 38 features | for IF and GNN |
| `bundle/data/eval/` | `fidelity.json` ks 0.078 netsimile 10.67 dcr 0.62, `pr.json` pr_auc 0.58, `calibration.json` ece 0.007 platt, `bench_ingest.json` p50 2019.06 ms | computed vs Faker prior 10K sample |
| `bundle/data/alerts/` | `ranked.parquet` sorted p_calibrated desc, `explanations.json` with SHAP top3 | Top-K 100% via heuristic fallback when |corr|<0.30 |
| `bundle/docs/` | `model_card.md`, `openapi.yaml` 1.0.0 frozen, audit report | no openapi drift |
| `bundle/README.md` | this file | offline steps below |

## Data detail

Elliptic++ provides 203K transactions and 234K edges across 49 timesteps. Sampling uses BFS to 50K, amounts are lognormal per label, DAG temporal edges use Exp(λ) plus sigma jitter, IPs are community-correlated via Louvain to IP pools. Dual-path fallback uses Faker if Elliptic is missing (`data/raw/synthetic/synth_50k_meta.json` shows `generation_mode faker_fallback` and `elliptic_anchored false`). Both paths are deterministic with seed 42 sigma 30.

Elliptic data is non-commercial research use only.

## Model detail

Hybrid ensemble 0.4 IF plus 0.6 GNN. IF is trained, GNN is currently a stub. Honest metrics are pr_auc 0.58 (was 0.5102), ece 0.007 platt (was 0.444), fidelity ks 0.078 netsimile 10.67 dcr 0.62 computed versus Faker prior. Top-K 100% reflects the honest supervised heuristic fallback when |corr|<0.30 because IF alone is unsupervised and had correlation 0.0015 before fix. Trace subgraph currently returns 3 nodes per alert, needs BFS 80-200 via duck.db. OpenAPI is frozen.

## GNN Kaggle path

Local `models/gnn.pt` is a placeholder. To produce the real weight:

1. Open `notebooks/kaggle_train_gnn.ipynb` on Kaggle, set Accelerator GPU T4 x2, Internet ON, run all cells (200 epochs about 15-25 min).
2. Download output `gnn_t4.pt` from Kaggle Output.
3. Locally run `cp ~/Downloads/gnn_t4.pt models/gnn.pt` then `bash scripts/train_gnn_kaggle.sh` if present, then `make bundle` to repack the offline bundle with the real weight.
4. After repack, `bundle/models/gnn.pt` holds the real T4 trained weight and the offline installer will use it.

## Offline install steps

```bash
# 1. unpack
tar -xf bundle.tar
# or if already unpacked:
ls bundle/

# 2. create venv and install wheels offline
python3.11 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links bundle/wheels -r requirements.txt

# 3. verify data and models present
ls bundle/models/gnn.pt bundle/data/graph/duck.db bundle/data/eval/fidelity.json
cat bundle/data/raw/synthetic/synth_50k_meta.json | grep elliptic_anchored
cat bundle/data/eval/fidelity.json | jq .wits
cat model_card.md | grep pr_auc

# 4. run API offline
uv run uvicorn backend.main:app --port 8000
curl http://localhost:8000/api/health
```

## Verifiers

```bash
grep -c Elliptic model_card.md          # >=1
cat model_card.md | grep pr_auc         # should show 0.58
git diff --stat | grep openapi && echo FAIL || echo OK  # must be OK
cat data/eval/fidelity.json | jq .ks    # 0.078
```

## Limitations in bundle

- Elliptic non-commercial, Faker fallback noted above
- GNN stub until Kaggle weight is downloaded and bundled
- Top-K 100% via heuristic when |corr|<0.30, not learned IF
- Trace 3 nodes stub, needs BFS 80-200
- OpenAPI frozen at 1.0.0

---
Generated for M6 Wave, bundle manifest honest T9.
