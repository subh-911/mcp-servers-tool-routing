.PHONY: help install install-dev run test coverage lint format clean docker-build docker-up docker-down

help:
	@echo "MCP Tool Router - Available Commands"
	@echo "====================================="
	@echo "make install       - Install production dependencies"
	@echo "make install-dev   - Install development dependencies"
	@echo "make run           - Run the application locally"
	@echo "make test          - Run tests"
	@echo "make coverage      - Run tests with coverage report"
	@echo "make lint          - Run linters"
	@echo "make format        - Format code with black and isort"
	@echo "make clean         - Clean up generated files"
	@echo "make docker-build  - Build Docker image"
	@echo "make docker-up     - Start Docker containers"
	@echo "make docker-down   - Stop Docker containers"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	python src/main.py

test:
	pytest

coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint:
	flake8 src/ tests/
	pylint src/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -f .coverage

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

dev: install-dev
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the application"

all: format lint test
	@echo "All checks passed!"
