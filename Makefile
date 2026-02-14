# Makefile for LeyChile ePub Generator
# Author: Luis Aguilera Arteaga <luis@aguilera.cl>

.PHONY: help install install-dev test lint format type-check clean build docs run

# Default target
help:
	@echo "🇨🇱 LeyChile ePub Generator - Development Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "📦 Installation:"
	@echo "  install        Install package in production mode"
	@echo "  install-dev    Install package with dev dependencies"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  test           Run tests with pytest"
	@echo "  test-cov       Run tests with coverage report"
	@echo "  lint           Run linters (ruff)"
	@echo "  format         Format code with black and isort"
	@echo "  format-check   Check code formatting"
	@echo "  type-check     Run type checking with mypy"
	@echo "  check          Run all checks (lint, format-check, type-check, test)"
	@echo ""
	@echo "🔨 Build & Release:"
	@echo "  build          Build distribution packages"
	@echo "  clean          Clean build artifacts"
	@echo ""
	@echo "🚀 Running:"
	@echo "  run URL=<url>  Generate ePub from URL"
	@echo "  example        Run with example law (Ley 18.700)"

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip

# Installation
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

install-all:
	$(PIP) install -e ".[all]"

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/leychile_epub --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report: htmlcov/index.html"

test-fast:
	pytest tests/ -v -x --tb=short

# Linting and formatting
lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check --diff src/ tests/
	isort --check-only --diff src/ tests/

type-check:
	mypy src/leychile_epub --ignore-missing-imports

# Validate SUPERIR NCG XMLs against schema
validate-superir:
	$(PYTHON) scripts/validate_superir.py --verbose

# All checks combined
check: format-check lint type-check test
	@echo "✅ All checks passed!"

# Building
build: clean
	$(PYTHON) -m build
	@echo "📦 Build complete: dist/"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "🧹 Cleaned build artifacts"

# Running
run:
ifndef URL
	@echo "❌ Error: URL is required"
	@echo "Usage: make run URL=https://www.leychile.cl/Navegar?idNorma=242302"
else
	leychile-epub "$(URL)"
endif

example:
	leychile-epub "https://www.leychile.cl/Navegar?idNorma=242302" -o ./output/
	@echo "📚 Example ePub generated in ./output/"

# Development helpers
dev-setup: install-dev
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Quick start:"
	@echo "  make test       - Run tests"
	@echo "  make check      - Run all checks"
	@echo "  make example    - Generate example ePub"

# Release helpers
version:
	@$(PYTHON) -c "from leychile_epub import __version__; print(__version__)"

bump-patch:
	@echo "Remember to update version in src/leychile_epub/__init__.py"

# Watch mode for development (requires watchdog)
watch:
	watchmedo auto-restart --patterns="*.py" --recursive -- pytest tests/ -v -x

# Documentation
docs:
	@echo "📖 Documentation: https://github.com/laguileracl/leychile-epub#readme"

# Pre-commit hook setup
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files
