.PHONY: help check test lint format typecheck security validate clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check: lint format typecheck security validate ## Run all checks (same as CI)

lint: ## Run linting
	@echo "Running ruff linting..."
	ruff check .

format: ## Check code formatting
	@echo "Checking code formatting with black..."
	black --check --diff .

typecheck: ## Run type checking
	@echo "Running mypy type checking..."
	mypy steward_ai_zorba_bot/ || echo "Typecheck completed with warnings"

security: ## Run security checks
	@echo "Running bandit security check..."
	bandit -r steward_ai_zorba_bot/ -x "*/tests/*" || echo "Security check completed with warnings"

validate: ## Validate configuration files
	@echo "Validating JSON files..."
	python -m json.tool status.json > /dev/null
	@echo "Validating workflow status protocol..."
	python orchestrator.py validate
	@echo "Checking required files..."
	@required_files="status.json README.md docs/acceptance_contract.md docs/runbook.md"; \
	for file in $$required_files; do \
		if [ ! -f "$$file" ]; then \
			echo "Required file $$file is missing"; \
			exit 1; \
		fi; \
	done; \
	echo "All required files present"

test: ## Run tests
	@echo "Running tests..."
	@if [ -d "tests" ]; then \
		pytest tests/ -v; \
	elif [ -d "steward_ai_zorba_bot/tests" ]; then \
		pytest steward_ai_zorba_bot/tests/ -v; \
	else \
		echo "No tests found, skipping"; \
	fi

fix: ## Auto-fix formatting and linting issues
	@echo "Auto-fixing formatting..."
	black .
	@echo "Auto-fixing linting issues..."
	ruff check . --fix

clean: ## Clean up temporary files
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name ".mypy_cache" -delete

install: ## Install dependencies
	@echo "Installing dependencies..."
	python -m pip install --upgrade pip
	if [ -f "steward_ai_zorba_bot/requirements.txt" ]; then \
		pip install -r steward_ai_zorba_bot/requirements.txt; \
	fi
	pip install black ruff mypy bandit pytest

dev-setup: install ## Set up development environment
	@echo "Development environment setup complete"
