.PHONY: check lint format typecheck test

# Default target runs all checks
check:
	@./check.sh

# Fast linting with Ruff
lint:
	python3 -m ruff check .

# Autoformat code
format:
	python3 -m ruff format .
	python3 -m ruff check --fix .

# Static type and import checking (Pylance engine)
typecheck:
	python3 -m pyright .

# Run Pytest suite
test:
	python3 -m pytest -v
