.DEFAULT_GOAL := help
SHELL := /bin/bash

PACKAGES := core geospatial agents evidence model_adapters

.PHONY: help setup setup-backend setup-packages setup-frontend dev dev-backend dev-frontend \
        test test-backend test-packages test-frontend lint fmt eval \
        clone-research download-models download-data demo up down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: setup-packages setup-backend setup-frontend ## Install all dependencies

setup-packages: ## Editable-install the workspace packages
	for p in $(PACKAGES); do python -m pip install -e "packages/$$p[dev]" || python -m pip install -e "packages/$$p"; done

setup-backend: ## Install backend deps (depends on packages)
	cd apps/backend && python -m pip install -e ".[dev]"

setup-frontend: ## Install frontend deps
	cd apps/frontend && npm install

dev: ## Run full stack via docker-compose
	docker compose up --build

dev-backend: ## Run API only
	cd apps/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend only
	cd apps/frontend && npm run dev

test: test-packages test-backend test-frontend ## Run all tests

test-packages: ## Run package tests
	for p in $(PACKAGES); do pytest "packages/$$p" || exit 1; done

test-backend: ## Run backend tests
	cd apps/backend && pytest

test-frontend: ## Run frontend tests
	cd apps/frontend && npm test

lint: ## Lint + format check
	ruff check packages apps/backend && black --check packages apps/backend
	cd apps/frontend && npm run lint

fmt: ## Auto-format
	ruff check --fix packages apps/backend && black packages apps/backend
	cd apps/frontend && npm run format

eval: ## Run the evaluation suite
	python evaluation/scripts/run_suite.py

clone-research: ## Clone the reference research repos into external/research/ (read-only)
	bash scripts/setup/clone_research_repos.sh

download-models: ## Fetch model checkpoints
	bash scripts/download_models/download_all.sh

download-data: ## Fetch demo + eval data
	bash scripts/download_data/download_all.sh

demo: ## Run the scripted demo
	bash scripts/demo/run_demo.sh

up: ## Start supporting services (db, redis, minio)
	docker compose up -d db redis minio

down: ## Stop all services
	docker compose down

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -not -path './external/*' -prune -exec rm -rf {} +
	rm -rf apps/backend/.pytest_cache .ruff_cache apps/frontend/dist apps/frontend/build
