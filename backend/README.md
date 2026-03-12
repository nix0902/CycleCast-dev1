# CycleCast Backend (Go)

Backend service for CycleCast - a financial cycle analysis system based on Larry Williams methodology.

## Architecture

Clean Architecture with layered design:

```
backend/
├── cmd/
│   └── api/           # Application entry point
├── internal/
│   ├── domain/        # Core business entities
│   ├── repository/    # Data access interfaces & implementations
│   ├── service/       # Business logic interfaces & implementations
│   └── infrastructure/# External dependencies (DB, Redis, gRPC)
├── pkg/               # Shared utilities
└── go.mod             # Go module definition
```

## Quick Start

```bash
# Install dependencies
cd backend && go mod download

# Run API server (requires .env or environment variables)
make run-api

# Run tests
make test-api

# Run linter
make lint-api
```

## Environment Variables

```env
# Server
ENV=development
API_PORT=8080
GIN_MODE=debug
LOG_LEVEL=info

# Database
DATABASE_URL=postgres://cyclecast:cyclecast@localhost:5432/cyclecast?sslmode=disable

# Redis
REDIS_URL=redis://localhost:6379/0

# Python Quant Service (gRPC)
QUANT_SERVICE_URL=localhost:9090

# Security (required for production)
JWT_SECRET=your-secret-key
VAULT_ADDR=http://localhost:8200
```

## API Endpoints

See [docs/API.md](../../docs/API.md) for complete REST/gRPC specification.

## Development

- Go 1.22+ required
- Use `gofmt` for formatting
- Run `go vet` before committing
- Write tests in `*_test.go` files

## Integration with Python Quant Service

The backend communicates with the Python quant service via gRPC:

- `quant/qspectrum/` - Spectral analysis (Burg's MEM)
- `quant/bootstrap/` - Bootstrap confidence intervals
- `quant/phenom/` - Phenomenological DTW analysis

See `internal/infrastructure/grpc/` for client implementation.
