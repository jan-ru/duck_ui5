.PHONY: help install install-dev setup-hooks format lint test clean run-all

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	uv pip install -e .

install-dev:  ## Install development dependencies
	uv pip install -e ".[dev]"

setup-hooks:  ## Install and setup pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✓ Pre-commit hooks installed"

hooks-run:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

hooks-update:  ## Update pre-commit hooks to latest versions
	pre-commit autoupdate

format:  ## Format code with ruff
	ruff format scripts/ tests/
	ruff check --fix scripts/ tests/

lint:  ## Lint code with ruff
	ruff check scripts/ tests/

type-check:  ## Type check with mypy
	mypy scripts/

test:  ## Run tests with pytest
	pytest tests/ -v

clean:  ## Clean generated files
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

run-all:  ## Run all transformation scripts
	@echo "Processing transaction dump..."
	python scripts/process_dump.py
	@echo "\nTransforming trial balances..."
	python scripts/transform_trial_balances.py
	@echo "\nCombining databases..."
	python scripts/combine_databases.py
	@echo "\n✓ All transformations complete!"
