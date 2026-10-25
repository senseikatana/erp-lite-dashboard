PY := backend/.venv/bin/python
UV := uv
NPM := npm --prefix frontend

.DEFAULT_GOAL := help

.PHONY: help setup setup-backend setup-frontend seed dev backend frontend test test-backend lint format clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: setup-backend setup-frontend ## Install backend and frontend dependencies

setup-backend: ## Create the Python virtualenv and install the API
	cd backend && $(UV) venv --python 3.13 .venv
	cd backend && $(UV) pip install -e ".[dev]"
	@test -f backend/.env || cp backend/.env.example backend/.env

setup-frontend: ## Install the Nuxt dependencies
	$(NPM) install --prefix frontend

seed: ## Load demo companies, users and activity
	cd backend && .venv/bin/python -m app.seed

dev: ## Run backend and frontend together (Ctrl-C stops both)
	@echo "Backend  -> http://localhost:8000/docs"
	@echo "Frontend -> http://localhost:3000 (3001 when 3000 is busy)"
	@trap 'kill 0' INT TERM; \
		(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
		($(NPM) run dev --prefix frontend) & \
		wait

backend: ## Run only the API with reload
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend: ## Run only the Nuxt dev server
	$(NPM) run dev --prefix frontend

test: test-backend ## Run the test suite

test-backend: ## Run the API tests
	cd backend && .venv/bin/python -m pytest -q

lint: ## Lint the backend
	cd backend && .venv/bin/ruff check app tests

format: ## Format the backend
	cd backend && .venv/bin/ruff format app tests

clean: ## Remove build artefacts and the local database
	rm -rf frontend/.nuxt frontend/.output backend/.pytest_cache backend/.ruff_cache
	rm -f backend/erp_lite.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +