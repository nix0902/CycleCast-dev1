.PHONY: all build run test clean docker vault db migrate seed

# =============================================================================
# CONFIGURATION
# =============================================================================
APP_NAME := cyclecast
VERSION := 3.2.0
GO_VERSION := 1.22
PYTHON_VERSION := 3.11

# Directories
BACKEND_DIR := backend
QUANT_DIR := quant
FRONTEND_DIR := frontend
DB_DIR := database
INFRA_DIR := infrastructure
DOCS_DIR := docs

# Docker
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_FILE := $(INFRA_DIR)/docker/docker-compose.yml

# Colors
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# =============================================================================
# DEFAULT
# =============================================================================
all: help

help:
	@echo "$(GREEN)CycleCast v$(VERSION) - Available Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)Development:$(RESET)"
	@echo "  make run              Start all services (API, Quant, Frontend)"
	@echo "  make run-api          Start Go API server"
	@echo "  make run-quant        Start Python Quant service"
	@echo "  make run-frontend     Start Next.js frontend"
	@echo ""
	@echo "$(YELLOW)Building:$(RESET)"
	@echo "  make build            Build all components"
	@echo "  make build-api        Build Go API binary"
	@echo "  make build-quant      Build Python package"
	@echo "  make build-frontend   Build Next.js production bundle"
	@echo ""
	@echo "$(YELLOW)Testing:$(RESET)"
	@echo "  make test             Run all unit tests"
	@echo "  make test-api         Run Go tests"
	@echo "  make test-quant       Run Python tests"
	@echo "  make test-frontend    Run frontend tests"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-coverage    Generate coverage report"
	@echo "  make bench            Run benchmarks"
	@echo ""
	@echo "$(YELLOW)Database:$(RESET)"
	@echo "  make db-up            Start database containers"
	@echo "  make db-down          Stop database containers"
	@echo "  make migrate-up       Apply migrations"
	@echo "  make migrate-down     Rollback migrations"
	@echo "  make migrate-create   Create new migration"
	@echo "  make seed             Load seed data"
	@echo "  make db-reset         Reset database (⚠️  destructive)"
	@echo ""
	@echo "$(YELLOW)Docker:$(RESET)"
	@echo "  make docker-up        Start all containers"
	@echo "  make docker-down      Stop all containers"
	@echo "  make docker-build     Build all images"
	@echo "  make docker-logs      Show container logs"
	@echo ""
	@echo "$(YELLOW)Infrastructure:$(RESET)"
	@echo "  make vault-start      Start Vault container"
	@echo "  make vault-init       Initialize Vault"
	@echo "  make vault-seal       Seal Vault"
	@echo "  make vault-unseal     Unseal Vault"
	@echo ""
	@echo "$(YELLOW)Code Quality:$(RESET)"
	@echo "  make lint             Run all linters"
	@echo "  make lint-api         Run Go linter"
	@echo "  make lint-quant       Run Python linter"
	@echo "  make fmt              Format all code"
	@echo ""
	@echo "$(YELLOW)Data:$(RESET)"
	@echo "  make import-data      Import market data"
	@echo "  make import-cot       Import COT data"
	@echo "  make generate-mocks   Generate mock data"
	@echo ""
	@echo "$(YELLOW)Utilities:$(RESET)"
	@echo "  make clean            Clean build artifacts"
	@echo "  make deps             Install all dependencies"
	@echo "  make env-check        Check environment setup"
	@echo "  make docs             Generate documentation"

# =============================================================================
# DEVELOPMENT
# =============================================================================
run: db-up
	@echo "$(GREEN)Starting all services...$(RESET)"
	@make -j3 run-api run-quant run-frontend

run-api:
	@echo "$(GREEN)Starting Go API server...$(RESET)"
	cd $(BACKEND_DIR) && go run ./cmd/api

run-quant:
	@echo "$(GREEN)Starting Python Quant service...$(RESET)"
	cd $(QUANT_DIR) && python main.py

run-frontend:
	@echo "$(GREEN)Starting Next.js frontend...$(RESET)"
	cd $(FRONTEND_DIR) && bun dev

# =============================================================================
# BUILDING
# =============================================================================
build: build-api build-quant build-frontend
	@echo "$(GREEN)All components built successfully!$(RESET)"

build-api:
	@echo "$(GREEN)Building Go API...$(RESET)"
	cd $(BACKEND_DIR) && \
		go build -ldflags="-X main.Version=$(VERSION)" -o bin/api ./cmd/api && \
		go build -ldflags="-X main.Version=$(VERSION)" -o bin/worker ./cmd/worker

build-quant:
	@echo "$(GREEN)Building Python package...$(RESET)"
	cd $(QUANT_DIR) && python -m build

build-frontend:
	@echo "$(GREEN)Building Next.js...$(RESET)"
	cd $(FRONTEND_DIR) && bun run build

# =============================================================================
# TESTING
# =============================================================================
test: test-api test-quant test-frontend
	@echo "$(GREEN)All tests passed!$(RESET)"

test-api:
	@echo "$(GREEN)Running Go tests...$(RESET)"
	cd $(BACKEND_DIR) && go test -v -race -coverprofile=coverage.out ./...

test-quant:
	@echo "$(GREEN)Running Python tests...$(RESET)"
	cd $(QUANT_DIR) && pytest --cov=. --cov-report=xml

test-frontend:
	@echo "$(GREEN)Running frontend tests...$(RESET)"
	cd $(FRONTEND_DIR) && bun test

test-integration:
	@echo "$(GREEN)Running integration tests...$(RESET)"
	cd $(BACKEND_DIR) && go test -v -tags=integration ./tests/integration/...

test-coverage:
	@echo "$(GREEN)Generating coverage report...$(RESET)"
	cd $(BACKEND_DIR) && go tool cover -html=coverage.out -o coverage.html
	@echo "$(GREEN)Coverage report: backend/coverage.html$(RESET)"

bench:
	@echo "$(GREEN)Running benchmarks...$(RESET)"
	cd $(BACKEND_DIR) && go test -bench=. -benchmem ./...

# =============================================================================
# DATABASE
# =============================================================================
db-up:
	@echo "$(GREEN)Starting database containers...$(RESET)"
	docker run -d --name cyclecast-postgres \
		-e POSTGRES_USER=cyclecast \
		-e POSTGRES_PASSWORD=cyclecast \
		-e POSTGRES_DB=cyclecast \
		-p 5432:5432 \
		postgres:16
	docker run -d --name cyclecast-redis \
		-p 6379:6379 \
		redis:7

db-down:
	@echo "$(YELLOW)Stopping database containers...$(RESET)"
	docker stop cyclecast-postgres cyclecast-redis 2>/dev/null || true
	docker rm cyclecast-postgres cyclecast-redis 2>/dev/null || true

migrate-up:
	@echo "$(GREEN)Applying migrations...$(RESET)"
	cd $(BACKEND_DIR) && go run ./cmd/cli migrate up

migrate-down:
	@echo "$(YELLOW)Rolling back migrations...$(RESET)"
	cd $(BACKEND_DIR) && go run ./cmd/cli migrate down

migrate-create:
	@read -p "Migration name: " name; \
	cd $(DB_DIR)/migrations && touch $$(date +%Y%m%d%H%M)_$$name.up.sql

seed:
	@echo "$(GREEN)Loading seed data...$(RESET)"
	psql -h localhost -U cyclecast -d cyclecast -f $(DB_DIR)/seeds/seed_all.sql

db-reset: db-down db-up migrate-up seed
	@echo "$(GREEN)Database reset complete!$(RESET)"

# =============================================================================
# DOCKER
# =============================================================================
docker-up:
	@echo "$(GREEN)Starting all containers...$(RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

docker-down:
	@echo "$(YELLOW)Stopping all containers...$(RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down

docker-build:
	@echo "$(GREEN)Building all images...$(RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) build

docker-logs:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f

# =============================================================================
# VAULT
# =============================================================================
vault-start:
	@echo "$(GREEN)Starting Vault...$(RESET)"
	docker run -d --name cyclecast-vault \
		-e VAULT_DEV_ROOT_TOKEN_ID=dev-root-token \
		-e VAULT_ADDR=http://0.0.0.0:8200 \
		-p 8200:8200 \
		hashicorp/vault:latest

vault-init:
	@echo "$(GREEN)Initializing Vault...$(RESET)"
	$(INFRA_DIR)/vault/scripts/setup.sh

vault-unseal:
	@echo "$(GREEN)Unsealing Vault...$(RESET)"
	vault operator unseal

vault-seal:
	@echo "$(YELLOW)Sealing Vault...$(RESET)"
	vault operator seal

# =============================================================================
# CODE QUALITY
# =============================================================================
lint: lint-api lint-quant lint-frontend
	@echo "$(GREEN)Linting complete!$(RESET)"

lint-api:
	@echo "$(GREEN)Linting Go code...$(RESET)"
	cd $(BACKEND_DIR) && golangci-lint run

lint-quant:
	@echo "$(GREEN)Linting Python code...$(RESET)"
	cd $(QUANT_DIR) && ruff check . && mypy .

lint-frontend:
	@echo "$(GREEN)Linting frontend...$(RESET)"
	cd $(FRONTEND_DIR) && bun run lint

fmt:
	@echo "$(GREEN)Formatting code...$(RESET)"
	cd $(BACKEND_DIR) && gofmt -w .
	cd $(QUANT_DIR) && black . && isort .
	cd $(FRONTEND_DIR) && bun run format

# =============================================================================
# DATA IMPORT
# =============================================================================
import-data:
	@echo "$(GREEN)Importing market data...$(RESET)"
	cd $(BACKEND_DIR) && go run ./cmd/cli import market-data

import-cot:
	@echo "$(GREEN)Importing COT data...$(RESET)"
	cd $(BACKEND_DIR) && go run ./cmd/cli import cot

generate-mocks:
	@echo "$(GREEN)Generating mock data...$(RESET)"
	cd $(BACKEND_DIR) && go generate ./...

# =============================================================================
# UTILITIES
# =============================================================================
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(RESET)"
	rm -rf $(BACKEND_DIR)/bin
	rm -rf $(BACKEND_DIR)/coverage.out
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

deps:
	@echo "$(GREEN)Installing dependencies...$(RESET)"
	cd $(BACKEND_DIR) && go mod download
	cd $(QUANT_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && bun install

env-check:
	@echo "$(GREEN)Checking environment...$(RESET)"
	@command -v go >/dev/null 2>&1 || { echo "$(RED)Go not installed$(RESET)"; exit 1; }
	@command -v python >/dev/null 2>&1 || { echo "$(RED)Python not installed$(RESET)"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "$(RED)Node not installed$(RESET)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)Docker not installed$(RESET)"; exit 1; }
	@echo "$(GREEN)All dependencies found!$(RESET)"

docs:
	@echo "$(GREEN)Generating documentation...$(RESET)"
	cd $(BACKEND_DIR) && go doc -all > $(DOCS_DIR)/api/godoc.txt
	cd $(QUANT_DIR) && pdoc -o $(DOCS_DIR)/quant .

# =============================================================================
# CI/CD
# =============================================================================
ci: deps lint test
	@echo "$(GREEN)CI pipeline complete!$(RESET)"

ci-deploy: build docker-build
	@echo "$(GREEN)Deployment artifacts ready!$(RESET)"
