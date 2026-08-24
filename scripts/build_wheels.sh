#!/usr/bin/env bash
set -euo pipefail
# BUILDKIT_PROGRESS=plain
# Description: quad wheel builder — common + cpu + rocm separate dirs
# Usage: bash scripts/build_wheels.sh [--dry-run]
# Common deps: geoip2, polars, duckdb, networkx, python-louvain, ijson, lxml, watchdog, python-magic, faker, fastapi, uvicorn, pydantic (+ sklearn if in requirements)

# quad pip download manylinux2014_x86_64 cp311 split wheels/cpu vs rocm
# - common: geoip2, polars, duckdb, networkx, python-louvain, ijson, lxml, watchdog, python-magic, faker, fastapi, uvicorn, pydantic (+ sklearn)
# - cpu: torch==2.4.1+cpu torchvision==0.19.1+cpu via download.pytorch.org/whl/cpu
# - rocm: torch torchvision torchaudio via repo.amd.com/rocm/whl-multi-arch + pyg extensions via Looong01

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p wheels/common wheels/cpu wheels/rocm

# ---------------------------------------------------------------------------
# Helper: run or echo depending on dry-run
# ---------------------------------------------------------------------------
run_or_echo() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    echo "+ $*"
    eval "$@"
  fi
}

# ---------------------------------------------------------------------------
# Common — pinned via requirements.cpu.txt but with platform quad — must use pip download NOT pip wheel
# quad pattern: manylinux2014_x86_64 + manylinux_2_28_x86_64 + any, cp311
# ---------------------------------------------------------------------------
COMMON_CMD="pip download --dest wheels/common --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 -r requirements.cpu.txt"

# ---------------------------------------------------------------------------
# CPU torch — via download.pytorch.org/whl/cpu
# ---------------------------------------------------------------------------
CPU_CMD="pip download --dest wheels/cpu --only-binary=:all: --platform manylinux2014_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 --index-url https://download.pytorch.org/whl/cpu torch==2.4.1+cpu torchvision==0.19.1+cpu || true"

# ---------------------------------------------------------------------------
# ROCm torch — via repo.amd.com/rocm/whl-multi-arch
# ---------------------------------------------------------------------------
ROCM_CMD="pip download --dest wheels/rocm --only-binary=:all: --platform manylinux2014_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 --index-url https://repo.amd.com/rocm/whl-multi-arch torch torchvision torchaudio --extra-index-url https://github.com/Looong01/pyg-rocm-build/releases pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv || true"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[dry-run] mkdir -p wheels/common wheels/cpu wheels/rocm"
  echo "[dry-run] ${COMMON_CMD}"
  echo "[dry-run] ${CPU_CMD}"
  echo "[dry-run] ${ROCM_CMD}"
  echo "[dry-run] Fallback: pip wheel --wheel-dir wheels/common --no-deps python-louvain || true"
  echo "[dry-run] Verification: pip install --dry-run --report /tmp/report.json --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt"
  echo "[dry-run] OFFLINE_TEST: python -m venv /tmp/offline_test && /tmp/offline_test/bin/pip install --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt"
else
  echo "==> Downloading common wheels (quad platform)..."
  # shellcheck disable=SC2086
  pip download --dest wheels/common --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 -r requirements.cpu.txt || {
    echo "WARN: common pip download failed (network/offline or missing binary), continuing"
  }

  echo "==> Downloading CPU torch wheels..."
  pip download --dest wheels/cpu --only-binary=:all: --platform manylinux2014_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 --index-url https://download.pytorch.org/whl/cpu torch==2.4.1+cpu torchvision==0.19.1+cpu || true

  echo "==> Downloading ROCm torch wheels..."
  pip download --dest wheels/rocm --only-binary=:all: --platform manylinux2014_x86_64 --platform any --python-version 3.11 --implementation cp --abi cp311 --index-url https://repo.amd.com/rocm/whl-multi-arch torch torchvision torchaudio --extra-index-url https://github.com/Looong01/pyg-rocm-build/releases pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv || true

  # Fallback: pip wheel for sdist-only packages (python-louvain if no wheel): pip wheel --wheel-dir wheels/common --no-deps <sdist> || true
  echo "==> Fallback: building sdist-only wheels if needed..."
  if ! ls wheels/common/python_louvain*.whl wheels/common/python-louvain*.whl 1>/dev/null 2>&1; then
    echo "  No python-louvain wheel found, attempting pip wheel fallback..."
    pip wheel --wheel-dir wheels/common --no-deps python-louvain || true
  fi
fi

# ---------------------------------------------------------------------------
# Write wheels/README.md manifest with counts and platform
# ---------------------------------------------------------------------------
set +o pipefail
COMMON_COUNT=$(ls -1 wheels/common/*.whl 2>/dev/null | wc -l | tr -d ' ')
CPU_COUNT=$(ls -1 wheels/cpu/*.whl 2>/dev/null | wc -l | tr -d ' ')
ROCM_COUNT=$(ls -1 wheels/rocm/*.whl 2>/dev/null | wc -l | tr -d ' ')
set -o pipefail
# Ensure empty counts become 0
COMMON_COUNT=${COMMON_COUNT:-0}
CPU_COUNT=${CPU_COUNT:-0}
ROCM_COUNT=${ROCM_COUNT:-0}
if [[ -z "${COMMON_COUNT}" ]]; then COMMON_COUNT=0; fi
if [[ -z "${CPU_COUNT}" ]]; then CPU_COUNT=0; fi
if [[ -z "${ROCM_COUNT}" ]]; then ROCM_COUNT=0; fi

COMMON_SIZE=$(du -sh wheels/common 2>/dev/null | cut -f1 || echo "0")
CPU_SIZE=$(du -sh wheels/cpu 2>/dev/null | cut -f1 || echo "0")
ROCM_SIZE=$(du -sh wheels/rocm 2>/dev/null | cut -f1 || echo "0")

cat > wheels/README.md <<EOF
# Offline Wheels Bundle — M6 Wave2 S2

Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Platform quad: manylinux2014_x86_64, manylinux_2_28_x86_64, any
Python: cp311 (3.11) — implementation cp, abi cp311
Builder: scripts/build_wheels.sh — pip download quad pattern (NOT pip wheel)

## Layout

- \`wheels/common/\` — common deps from requirements.cpu.txt (geoip2, polars, duckdb, networkx, python-louvain, ijson, lxml, watchdog, python-magic, faker, fastapi, uvicorn, pydantic, scikit-learn, shap, jinja2, etc.)
- \`wheels/cpu/\` — CPU torch via https://download.pytorch.org/whl/cpu (torch==2.4.1+cpu, torchvision==0.19.1+cpu)
- \`wheels/rocm/\` — ROCm torch via https://repo.amd.com/rocm/whl-multi-arch + pyg extensions via https://github.com/Looong01/pyg-rocm-build/releases

## Counts

- common: ${COMMON_COUNT} wheels (${COMMON_SIZE})
- cpu: ${CPU_COUNT} wheels (${CPU_SIZE})
- rocm: ${ROCM_COUNT} wheels (${ROCM_SIZE})
- total: $((COMMON_COUNT + CPU_COUNT + ROCM_COUNT)) wheels

## Verification

\`\`\`bash
# Dry-run report (no network, uses local wheels only):
pip install --dry-run --report /tmp/report.json --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt

# Offline venv verification:
python -m venv /tmp/offline_test && /tmp/offline_test/bin/pip install --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt
\`\`\`

## Notes

- Uses \`pip download\` with \`--platform manylinux2014_x86_64\` quad — never \`pip wheel\` with platform.
- \`wheels/cpu\` and \`wheels/rocm\` are separate dirs — local version identifier (+cpu vs +rocm) would collide in a flat dir.
- ROCm download is best-effort (\`|| true\`) — CI may run without GPU wheels.
- sdist fallback: \`pip wheel --wheel-dir wheels/common --no-deps <sdist>\` only for packages with no binary wheel (e.g. python-louvain).

## File lists

EOF

echo "" >> wheels/README.md
echo "### wheels/common" >> wheels/README.md
if ls wheels/common/*.whl 1>/dev/null 2>&1; then
  ls -1 wheels/common/*.whl 2>/dev/null | head -n 100 >> wheels/README.md || true
  echo "" >> wheels/README.md
else
  echo "(empty — run without --dry-run to populate)" >> wheels/README.md
  echo "" >> wheels/README.md
fi
echo "### wheels/cpu" >> wheels/README.md
if ls wheels/cpu/*.whl 1>/dev/null 2>&1; then
  ls -1 wheels/cpu/*.whl 2>/dev/null | head -n 100 >> wheels/README.md || true
  echo "" >> wheels/README.md
else
  echo "(empty — run without --dry-run to populate)" >> wheels/README.md
  echo "" >> wheels/README.md
fi
echo "### wheels/rocm" >> wheels/README.md
if ls wheels/rocm/*.whl 1>/dev/null 2>&1; then
  ls -1 wheels/rocm/*.whl 2>/dev/null | head -n 100 >> wheels/README.md || true
  echo "" >> wheels/README.md
else
  echo "(empty — run without --dry-run to populate)" >> wheels/README.md
  echo "" >> wheels/README.md
fi

echo "Wrote wheels/README.md (common=${COMMON_COUNT} cpu=${CPU_COUNT} rocm=${ROCM_COUNT})"

# ---------------------------------------------------------------------------
# Verification: pip install --dry-run --report (best-effort, log only)
# ---------------------------------------------------------------------------
echo "==> Verification (best-effort): pip install --dry-run --report /tmp/report.json --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[dry-run] pip install --dry-run --report /tmp/report.json --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt"
else
  pip install --dry-run --report /tmp/report.json --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt 2>&1 | head -n 50 || echo "WARN: verification dry-run failed (expected if wheels not yet populated)"
fi

# Must handle offline venv verification: after download, log offline venv command
echo "OFFLINE_TEST: python -m venv /tmp/offline_test && /tmp/offline_test/bin/pip install --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt"

# Optional actual offline venv test if not dry-run and wheels are populated
if [[ "${DRY_RUN}" -eq 0 ]] && [[ "${COMMON_COUNT}" -gt 0 ]]; then
  echo "==> Attempting offline venv install test (best-effort)..."
  rm -rf /tmp/offline_test 2>/dev/null || true
  if python3 -m venv /tmp/offline_test 2>&1; then
    /tmp/offline_test/bin/pip install --no-index --find-links wheels/common --find-links wheels/cpu -r requirements.cpu.txt 2>&1 | tail -n 20 || echo "WARN: offline venv install failed (may need more wheels or network)"
  else
    echo "WARN: python -m venv failed, skipping offline venv test"
  fi
fi

echo "Done."
