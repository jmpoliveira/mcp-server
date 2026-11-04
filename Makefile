.DEFAULT_GOAL := help
.PHONY: help install run test lint format typecheck check docker-up docker-down clean

PYTHON ?= python

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install the project with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"

run: ## Run the server locally (reads .env)
	$(PYTHON) main.py

test: ## Run the test suite
	$(PYTHON) -m pytest

lint: ## Check style and common bugs
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format: ## Apply formatting and safe fixes
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

typecheck: ## Static type check
	$(PYTHON) -m pyright --pythonpath "$$($(PYTHON) -c 'import sys; print(sys.executable)')"

check: lint typecheck test ## Everything CI runs

docker-up: ## Start the server and Jaeger
	docker compose up --build

docker-down: ## Stop and remove the containers
	docker compose down

clean: ## Remove caches and build output
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache logs
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
