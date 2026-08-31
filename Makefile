.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help setup setup-backend setup-frontend dev dev-backend dev-frontend \
        test test-backend test-frontend lint fmt eval \
        download-models download-data demo up down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: setup-backend setup-frontend ## Install all dependencies

setup-backend: ## Install backend deps
	cd backend && python -m pip install -e ".[dev]"

setup-frontend: ## Install frontend deps
	cd frontend && npm install

dev: ## Run full stack via docker-compose
	docker compose up --build

dev-backend: ## Run API only
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend only
	cd frontend && npm run dev

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

lint: ## Lint + format check
	cd backend && ruff check . && black --check .
	cd frontend && npm run lint

fmt: ## Auto-format
	cd backend && ruff check --fix . && black .
	cd frontend && npm run format

eval: ## Run the evaluation suite
	python evaluation/scripts/run_suite.py

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
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/.ruff_cache frontend/dist frontend/build
