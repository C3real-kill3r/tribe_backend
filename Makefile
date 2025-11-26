.PHONY: help install run dev test clean migrate migrate-up migrate-down docker-up docker-down docker-build

# Default target
help:
	@echo "Tribe Backend - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make run         - Run the development server"
	@echo "  make dev         - Run with auto-reload (default)"
	@echo "  make test        - Run tests"
	@echo "  make clean        - Clean Python cache files"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-up   - Upgrade database to head"
	@echo "  make migrate-down - Downgrade database one revision"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make docker-build - Build Docker images"
	@echo ""

# Install dependencies
install:
	@echo "Installing dependencies..."
	python3 -m venv venv || true
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt

# Run development server
run:
	@echo "Starting development server..."
	. venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run with auto-reload
dev:
	@echo "Starting development server with auto-reload..."
	. venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	@echo "Running tests..."
	. venv/bin/activate && pytest

# Clean Python cache
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "Clean complete"

# Database migrations
migrate:
	@echo "Running database migrations..."
	. venv/bin/activate && alembic upgrade head

migrate-up:
	@echo "Upgrading database to head..."
	. venv/bin/activate && alembic upgrade head

migrate-down:
	@echo "Downgrading database one revision..."
	. venv/bin/activate && alembic downgrade -1

# Docker commands
docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

# Format code
format:
	@echo "Formatting code..."
	. venv/bin/activate && black app/ tests/ || echo "black not installed, skipping..."

# Lint code
lint:
	@echo "Linting code..."
	. venv/bin/activate && flake8 app/ tests/ || echo "flake8 not installed, skipping..."

