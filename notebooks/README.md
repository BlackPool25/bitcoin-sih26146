# notebooks — Kaggle T4 GNN Training

## Purpose
Train `M3_GCN 38→64→32` on real graph+features (Kaggle T4 x2) to replace the 73B stub `models/gnn.pt`. See `model_card.md` Limitations: “GNN not trained at finale” — this makes the hybrid `0.4/0.6` (IF+GNN) honest.

## Quickstart: Upload to Kaggle

1. **Create Notebook** on kaggle.com → New Notebook → Upload `kaggle_train_gnn.ipynb`
   - Or: File → Import Notebook → paste file content

2. **Settings (right panel)**
   - **Accelerator:** `GPU T4 x2` (16 GB x2)
   - **Internet:** `ON` (needed for `pip install` + `git clone`)
   - Quota: 30 h/week, 9 h/session — training 200 epochs ≈ 15–25 min on T4

3. **Run**
   - Run cells 1→6 sequentially. Cell 4 logs per-epoch loss; artifact saved to `/kaggle/working/gnn_t4.pt` (1–5 MB).

4. **Download**
   - After Cell 6: Output → Files → `gnn_t4.pt` (also `calibrator_t4.pkl`, `pr_t4.json`) → Download

5. **Bundle back locally**
   ```bash
   cp ~/Downloads/gnn_t4.pt ./gnn_t4.pt
   bash scripts/train_gnn_kaggle.sh            # verifies >1M, copies to models/gnn.pt, runs make eval
   # or: bash scripts/train_gnn_kaggle.sh /path/to/gnn_t4.pt
   make bundle
   ls -lh models/gnn.pt
   cat data/eval/pr.json | jq .pr_auc          # expect 0.65–0.75 vs 0.51 stub
   ```

## Expected Output

| Step | Artifact | Size | Metric |
|------|----------|------|--------|
| Cell 4 `models/gnn.pt` | GNN weights | 1–5 MB (stub was 73 B) | loss ↓, early stopping if overfit |
| Cell 5 `data/eval/pr.json` | PR-AUC (DFRWS 70/30 temporal+graph-disjoint) | — | `pr_auc` 0.65–0.75 (vs 0.51 stub), `ece` <0.1 |
| Cell 5 `fuse(0.6,0.8)==0.72` | Ensemble 0.4/0.6 check | — | `python ml/ensemble.py --check` passes |
| Cell 6 `/kaggle/working/gnn_t4.pt` | Downloadable | 1–5 MB | `sha256sum` printed |

## Offline Bundle Steps

1. After downloading, verify and promote:
   ```bash
   sha256sum ~/Downloads/gnn_t4.pt
   bash scripts/train_gnn_kaggle.sh ~/Downloads/gnn_t4.pt
   ls -lh models/gnn.pt          # >1M
   uv run python ml/ensemble.py --check
   ```
2. Re-eval and bundle:
   ```bash
   make eval                      # pr_auc uplift visible
   make bundle
   ls -R dist | head -n 40
   ```

## Fallback to CPU (if T4 quota exceeded)

- **Kaggle:** Settings → Accelerator `None` (CPU) — training still works via `ml/train_gnn.py --train` CPU fallback, slower (200 epochs ≈ 1–2 h on CPU). Cells handle this: Cell 4 tries `--device cuda` then falls back to `--train --edge_db data/graph/duck.db` with synthetic `_build_edge_index` chain+self-loops if `duck.db` absent.
- **Local:** No T4 needed for smoke test:
  ```bash
  uv run python ml/train_gnn.py --train --out /tmp/gnn_smoke.pt
  ls -lh /tmp/gnn_smoke.pt        # >1K
  # legacy alias used in CI verifier (if supported):
  uv run python ml/train_gnn.py --device cpu --epochs 2 --out /tmp/gnn_smoke.pt || uv run python ml/train_gnn.py --train --out /tmp/gnn_smoke.pt
  ```
- **Without Kaggle API key:** Notebook creation/upload is manual via browser (no `kaggle` CLI needed). Data upload works via git clone (Internet ON) OR via **Input → Add Input → Dataset** (`/kaggle/input/elliptic/*`) — notebook copies from `/kaggle/input` if git unavailable (offline bundle).

## Data Sources (notebook handles both)

- **Option A (Internet ON):** `!git clone https://github.com/<you>/sih26146.git` → `data/raw/synthetic/synth_50k.csv` + `data/graph/duck.db`
- **Option B (Kaggle Dataset, no Internet needed once attached):** Attach dataset containing `data/` snapshot → notebook does `!cp -r /kaggle/input/elliptic/* data/raw/elliptic/` and generic `/kaggle/input/*/data` → `./data` + `*.parquet`/`*.db` fallbacks. Works even if git clone fails.

## Verify Notebook

```bash
ls -lh notebooks/kaggle_train_gnn.ipynb
jupyter nbconvert --to script notebooks/kaggle_train_gnn.ipynb --stdout | head -n 50   # no error
uv run basedpyright notebooks/kaggle_train_gnn.ipynb 2>&1 | tail -n 20 || true
uv run python ml/train_gnn.py --train --out /tmp/gnn_smoke.pt && ls -lh /tmp/gnn_smoke.pt
bash scripts/train_gnn_kaggle.sh gnn_t4.pt   # after download
```

## Troubleshooting

- `pip install` slow: Kaggle caches wheels; re-run — second run is cached.
- `torch.cuda.is_available()==False`: Check Settings → Accelerator is T4 x2, not None. Re-run Cell 1.
- `data/raw/synthetic` missing: Add Kaggle Dataset input or ensure Internet ON for git clone; check `ls /kaggle/input` in Cell 2 output.
- `models/gnn.pt` still 73B after Cell 4: Training fell back to stub (torch import failed) — reinstall `torch_geometric` stack in Cell 1 and re-run.
- `pr_auc` still 0.51: GNN not used in `scripts/eval/pr.py` fallback path (IF-only mock) — ensure `models/gnn.pt` >1M and re-run `ml/calibrate.py`.

## References

- `ml/train_gnn.py` — M3_GCN 38→64→32, `TORCH_BLAS_PREFER_HIPBLASLT` guard, CPU fallback, `_build_edge_index`, `weights_only=True` + `map_location="cpu"`.
- `ml/features.py` — 38 frozen features.
- `ml/ensemble.py` — fuse 0.4/0.6, `fuse(0.6,0.8)==0.72`, XGB 0.669 hedge.
- `pyproject.toml` — deps (polars, duckdb, networkx, scikit-learn).
- `model_card.md` — Limitations “GNN not trained at finale”.
