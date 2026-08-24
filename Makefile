.PHONY: lint typecheck test bench ingest-bench docker-build bundle eval offline-check bench-eval help

PY ?= python
UV ?= uv

help:
	@grep -E "^[a-z-]+:.*?##" Makefile || grep -E "^[a-z-]+:" Makefile

lint:
	$(UV) run ruff check . --fix
	$(UV) run ruff format --check . || $(UV) run ruff format .

typecheck:
	$(UV) run basedpyright

test:
	$(UV) run pytest -q

bench:
	$(UV) run $(PY) scripts/bench_ingest.py --scale 50k --formats csv --runs 3 --out bench.json
	@$(UV) run $(PY) -c "import json,sys; d=json.load(open('bench.json')); p=d.get('p50_ms') if d.get('p50_ms') is not None else d.get('formats',{}).get('csv',{}).get('p50_ms'); print(f'[bench] csv p50={p} ms thr=2000'); sys.exit(0 if p is not None and float(p)<2000 else 1)"
	@ls -lh bench.json
	@cat bench.json | $(UV) run $(PY) -m json.tool | head -n 40

ingest-bench: bench
	@echo "[ingest-bench] alias for bench"

docker-build:
	docker compose build --progress=plain
	@echo "docker-build OK"

bundle:
	bash scripts/bundle.sh
	@echo "bundle OK"

eval:
	uv run python scripts/eval/pr.py --split dfrws --out data/eval/pr.json && uv run python scripts/eval/stress.py --inject 200 --out data/eval/stress.json && uv run python scripts/eval/sigma_sweep.py --sigmas 5,30,120 --out data/eval/sigma_sweep.json
	@echo "eval OK"

offline-check:
	bash tests/test_offline.sh
	@echo "offline-check OK"

bench-eval:
	uv run python scripts/eval/bench/ingest_bench.py --out data/eval/bench_ingest.json && uv run python scripts/eval/bench/viz_bench.py --out data/eval/bench_viz.json && uv run python scripts/eval/bench/rocm_parity_bench.py --out data/eval/bench_rocm.json
	@echo "bench-eval OK"
