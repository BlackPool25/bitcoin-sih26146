.PHONY: lint typecheck test bench ingest-bench help

PY ?= python
UV ?= uv

help:
	@echo "Targets: lint typecheck test bench ingest-bench"

lint:
	$(UV) run ruff check . --fix
	$(UV) run ruff format --check . || $(UV) run ruff format .

typecheck:
	$(UV) run basedpyright

test:
	$(UV) run pytest -q

bench:
	@if [ -f scripts/bench_ingest.py ]; then \
		$(PY) scripts/bench_ingest.py --scale 50k --formats csv,json,xml; \
	else \
		echo "[bench] scripts/bench_ingest.py not yet present — stub OK (M1 T12 will create)"; \
	fi

ingest-bench: bench
	@echo "[ingest-bench] alias for bench"
