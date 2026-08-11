.PHONY: check smoke test validate asset-check lint format typecheck cpp-test examples clean

check: test validate asset-check cpp-test

smoke:
	PYTHONPATH=src python -m dxai smoke --episodes 3 --agent heuristic

test:
	PYTHONPATH=src pytest -q

validate:
	PYTHONPATH=src python scripts/validate_artifacts.py

asset-check:
	PYTHONPATH=src python scripts/check_no_assets.py

examples:
	PYTHONPATH=src python scripts/generate_examples.py

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts

typecheck:
	mypy src/dxai

cpp-test:
	cmake -S engine_adapter -B build/bridge -DCMAKE_BUILD_TYPE=Release
	cmake --build build/bridge --config Release --parallel
	ctest --test-dir build/bridge -C Release --output-on-failure

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache
	find artifacts -mindepth 1 ! -name .gitkeep ! -name README.md -delete 2>/dev/null || true
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
