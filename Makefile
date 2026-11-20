.PHONY: clean-cache-temp-files \
        setup \
        lint code-check \
        test \
        format format-check \
        doc \
        pipeline all

.DEFAULT_GOAL := all

PATH_SOURCE ?= degiro_renta
PATH_TESTS ?= tests
PATH_PROJECT_ROOT ?= .

clean-cache-temp-files:
	@echo "Cleaning cache and temporary files..."
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type d -name .pytest_cache -exec rm -rf {} +
	@find . -type d -name .mypy_cache -exec rm -rf {} +
	@find . -type d -name .complexipy_cache -exec rm -rf {} +
	@find . -type d -name .ruff_cache -exec rm -rf {} +
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@rm -rf .cache site
	@echo "✅ Clean complete."

setup:
	@echo "Installing dependencies..."
	@uv sync --all-groups
	@npm ci --silent
	@uv run pre-commit install
	@echo "✅ Dependencies installed."

lint:
	@echo "Running lint checks..."
	@uv run ruff format $(PATH_PROJECT_ROOT)
	@uv run ruff check --fix $(PATH_PROJECT_ROOT)
	@echo "✅ Linting complete."

code-check:
	@echo "Running static code checks..."
	@uv run complexipy -f $(PATH_PROJECT_ROOT)
	@uv run mypy $(PATH_SOURCE)
	@echo "✅ Code checks complete."

test:
	@echo "Running tests..."
	@uv run pytest $(PATH_TESTS) --maxfail=1 --durations=0
	@echo "✅ Tests complete."

format:
	@echo "Formatting documents and configuration with Prettier..."
	@npx prettier --write .
	@echo "✅ Formatting complete."

format-check:
	@echo "Checking format with Prettier..."
	@npx prettier --check .
	@echo "✅ Format check complete."

doc:
	@echo "Serving documentation..."
	@uv run zensical serve

pipeline: setup clean-cache-temp-files lint format code-check
	@echo "✅ Pipeline complete."

all: pipeline test
	@echo "✅ All tasks complete."
