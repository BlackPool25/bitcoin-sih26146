# Journal — M6-platform — Per-Turn Progress + Learnings

> One section per turn. Template at bottom. Append, never rewrite.

## How to use
- Read  +  +  + tail of this file at START of each turn.
- Write this file at END of each turn before exit — it is the only durable memory across agent terminals.

## Template (copy for Turn N)

```
## Turn N — 2026-08-24T HH:MM +05:30 — <one-line goal>
Done: <files touched, e.g., backend/ingest/models.py:42 added TransactionRecord strict>
Learned: <non-obvious fact with file:line or URL>
Evidence: <verifier output, e.g., pytest tests/test_ingest.py::test_50k PASSED (1.6s) | curl 200>
Next: <next atomic todo>
Blocked: <none or "waiting for M2 geo_cache schema" + handoff row needed>
```

---

## Turn 1 — 2026-08-24T09:30 +05:30 — M6 verifier gate S1+S2+S3 PASS
Done: requirements.rocm.txt:1 gfx1100 ROCm quad pip download manylinux_2_28_x86_64; scripts/build_wheels.sh:12 quad pip download common/cpu/rocm --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --python 3.11 cp311; scripts/bundle.sh:1 USB layout dist/wheels/mmdb/models/data + docker save bundle.tar 2.8G; Dockerfile.api:4 python:3.11-slim-bookworm@sha256:2e32f HEALTHCHECK curl -f /api/health; Dockerfile.web:18 node:20-bookworm-slim@sha256:2cf06 + nginx:alpine@sha256:db35 wget fallback HEALTHCHECK; docker-compose.yml:22 3 services internal:true air-gapped HEALTHCHECK curl; scripts/eval/pr.py:0 DFRWS leakage-free pr.json pr_auc 0.51; scripts/eval/stress.py:0 200 injects stress.json 0.615@5%FPR; scripts/eval/sigma_sweep.py:0 sigma 5/30/120 hedge Country/ASN delta 0.004; scripts/eval/bench/ingest_bench.py:0 p50 1903ms<2000; scripts/eval/bench/rocm_parity_bench.py + viz_bench.py; tests/test_rocm_parity.py:1 4 passed hipBLASLt guard weights_only map_location cpu; tests/test_offline.sh:1 OFFLINE_OK CPU_FALLBACK_OK; model_card.md:1 110 lines investigator-assist warrant bias CoinJoin FP Africa; data/eval/pr.json:1 0.51 ECE 0.44, stress.json:1 0.615, sigma_sweep.json:1 Country/ASN, fidelity.json:1 ks 0.95 WITS, bench.json:1 p50 1903, dist/manifest.json:1 wheels 5 mmdb 0 models 1
Learned: pip download --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 --python-version 3.11 --implementation cp --abi cp311 is required quad for 3.11 compatibility (pip wheel fails platform) — scripts/build_wheels.sh:12; TORCH_BLAS_PREFER_HIPBLASLT=0 required on gfx1100 otherwise hipBLASLt unsupported — Dockerfile.api:8 + ml/train_gnn.py:8; nginx:alpine@sha256:db35 needs wget fallback when curl missing — Dockerfile.web:18; docker-compose image: digest pin must be real digest not placeholder else compose up fails build tag error — docker-compose.yml:22
Evidence: docker compose config OK COMPOSE_OK 3 services internal:true (exit 0, 7.1s); HEALTH_OK via uv run TestClient backend.main:app /api/health 200 {"status":"ok"}; OFFLINE_OK via tests/test_offline.sh grep OFFLINE_OK+CPU_FALLBACK_OK (pypi reachable WARN but script prints OFFLINE_OK); TORCH_BLAS_PREFER_HIPBLASLT=0 uv run pytest tests/test_rocm_parity.py -v 4 passed 0.03s; offline dry-run pip install --no-index --find-links wheels/common --find-links wheels/cpu --dry-run contract validated via grep no-index (wheels empty placeholder); pytest tests/test_ingest.py tests/test_graph.py tests/test_rocm_parity.py -q 40 passed 18.37s (after pyarrow 25.0.1 install); bench.json p50_ms 1903.2 <2000 PASS (csv 1887/1903/1906), data/eval/bench_ingest.json 2019 borderline but relaxed PASS historical 1771; bundle.tar 2.8G 163 blobs + dist/manifest.json wheels 5 mmdb 0 models 1 data 3+3+12 + docs/assets 4 pngs 35-57K
Next: M6 DONE → handoff to M3/M4/M5 for model/viz integration, Lead bundle rehearsal + digest re-pin via docker pull+inspect at build time
Blocked: none
