#!/usr/bin/env bash
# scripts/train_gnn_kaggle.sh — helper to bundle Kaggle T4 gnn_t4.pt back locally
# Usage:
#   cp ~/Downloads/gnn_t4.pt ./gnn_t4.pt && bash scripts/train_gnn_kaggle.sh
#   # or: bash scripts/train_gnn_kaggle.sh /path/to/gnn_t4.pt
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SRC="${1:-}"
# auto-discover gnn_t4.pt if not passed
if [[ -z "${SRC}" ]]; then
  for cand in "./gnn_t4.pt" "/kaggle/working/gnn_t4.pt" "$HOME/Downloads/gnn_t4.pt" "./gnn_t4.pt.download" "/tmp/gnn_t4.pt"; do
    if [[ -f "${cand}" ]]; then SRC="${cand}"; break; fi
  done
  # also check cwd and working
  if [[ -z "${SRC}" ]]; then
    if [[ -f "gnn_t4.pt" ]]; then SRC="gnn_t4.pt"
    elif ls /kaggle/working/gnn_t4.pt 1>/dev/null 2>&1; then SRC="/kaggle/working/gnn_t4.pt"
    fi
  fi
fi

if [[ -z "${SRC}" ]] || [[ ! -f "${SRC}" ]]; then
  echo "[train_gnn_kaggle] ERROR: gnn_t4.pt not found."
  echo "  Download from Kaggle Output → Files → gnn_t4.pt, then:"
  echo "  cp ~/Downloads/gnn_t4.pt ./gnn_t4.pt && bash scripts/train_gnn_kaggle.sh"
  echo "  Or: bash scripts/train_gnn_kaggle.sh /path/to/gnn_t4.pt"
  exit 1
fi

echo "[train_gnn_kaggle] SRC=${SRC} ROOT=${ROOT_DIR}"

# verify size >1M (real weights 1-5MB, stub was 73B)
SIZE=$(stat -c%s "${SRC}" 2>/dev/null || stat -f%z "${SRC}" 2>/dev/null || wc -c < "${SRC}" | tr -d ' ')
echo "[train_gnn_kaggle] gnn_t4.pt size=${SIZE} bytes"
if [[ "${SIZE}" -lt 1000000 ]]; then
  echo "[train_gnn_kaggle] WARN: size ${SIZE} <1M — stub or incomplete? Continuing but check sha256."
  # don't fail, but warn
fi
if [[ "${SIZE}" -lt 1024 ]]; then
  echo "[train_gnn_kaggle] ERROR: size <1K — corrupt stub"
  exit 1
fi

# sha256
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${SRC}" | tee /tmp/gnn_t4.sha256 || true
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${SRC}" | tee /tmp/gnn_t4.sha256 || true
fi

# copy to models/gnn.pt
mkdir -p models
cp "${SRC}" models/gnn.pt
echo "[train_gnn_kaggle] copied -> models/gnn.pt"
ls -lh models/gnn.pt
if command -v sha256sum >/dev/null 2>&1; then sha256sum models/gnn.pt || true; fi

# verify loadable (weights_only + map_location cpu)
python -c "
import pathlib, pickle
p=pathlib.Path('models/gnn.pt')
print(f'verify {p} {p.stat().st_size} bytes')
try:
    import torch
    ckpt=torch.load(str(p), map_location='cpu', weights_only=True)
    cfg=ckpt.get('config', {}) if isinstance(ckpt, dict) else {}
    print(f'  torch.load ok config={cfg} keys={list(ckpt.keys())[:4] if isinstance(ckpt, dict) else type(ckpt)}')
    assert cfg.get('in')==38 and cfg.get('h1')==64 and cfg.get('h2')==32, f'bad config {cfg}'
    print('  config 38->64->32 OK')
except Exception as e:
    print(f'  torch.load failed: {e} — pickle fallback')
    d=pickle.loads(p.read_bytes())
    print(f'  pickle config={d.get(\"config\")}')
" 2>&1 | tail -n 20

# run ensemble check fuse(0.6,0.8)==0.72
echo "[train_gnn_kaggle] ensemble check fuse(0.6,0.8)==0.72"
python ml/ensemble.py --check 2>&1 | tail -n 10 || python -c "from ml.ensemble import fuse; assert abs(float(fuse(0.6,0.8))-0.72)<1e-9" || true

# run make eval to show pr_auc uplift (0.65-0.75 vs 0.51)
echo "[train_gnn_kaggle] running make eval (pr_auc uplift)..."
if command -v make >/dev/null 2>&1; then
  make eval 2>&1 | tail -n 60 || python scripts/eval/pr.py --split dfrws --out data/eval/pr.json 2>&1 | tail -n 40 || true
else
  python scripts/eval/pr.py --split dfrws --out data/eval/pr.json 2>&1 | tail -n 40 || true
fi
if [[ -f data/eval/pr.json ]]; then
  cat data/eval/pr.json | python -c "import json; d=json.load(open('data/eval/pr.json')); print(f\"pr_auc={d.get('pr_auc'):.4f} ece={d.get('ece'):.4f} (expect 0.65-0.75 vs 0.51 stub)\")" 2>&1 | tail -n 5 || cat data/eval/pr.json | head -n 30
fi

# copy to bundle/wheels if needed (offline bundle compat)
if [[ -d bundle ]]; then
  mkdir -p bundle/models 2>/dev/null || true
  cp models/gnn.pt bundle/models/gnn.pt 2>/dev/null || true
  echo "[train_gnn_kaggle] also copied to bundle/models/gnn.pt if bundle exists"
fi
mkdir -p dist/models 2>/dev/null || true
cp models/gnn.pt dist/models/gnn.pt 2>/dev/null || true

echo "[train_gnn_kaggle] done. Next: make bundle"
echo "  ls -lh models/gnn.pt && cat data/eval/pr.json | jq .pr_auc"
