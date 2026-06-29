.PHONY: install backend-dev frontend-dev agent-dev test lint lint-python lint-frontend lint-agent build-frontend build-agent clean

# Python paths (Windows venv)
PYTHON := backend/venv/Scripts/python
PIP := backend/venv/Scripts/pip

install: ## Install all dependencies
	$(PIP) install -r backend/requirements.txt
	cd frontend && npm install
	cd agent && npm install

backend-dev: ## Start FastAPI dev server
	$(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Start Vite dev server
	cd frontend && npm run dev

agent-dev: ## Start Electron in dev mode
	cd agent && npm start

test: ## Run all tests
	cd backend && $(PYTHON) -m pytest backend/
	cd frontend && npm test -- --run

lint: lint-python lint-frontend lint-agent ## Run all linters

lint-python: ## Run Python linters (ruff + mypy)
	ruff check backend/
	mypy --strict backend/

lint-frontend: ## Run ESLint on frontend
	cd frontend && npm run lint

lint-agent: ## Run ESLint on agent
	cd agent && npm run lint

build-frontend: ## Production build for frontend
	cd frontend && npm run build

build-agent: ## Production build for agent
	cd agent && npm run build

clean: ## Remove build artifacts and cache
	-rm -rf frontend/dist agent/dist
	-find backend -type d -name __pycache__ -exec rm -rf {} +
	-find backend -type f -name '*.pyc' -delete
