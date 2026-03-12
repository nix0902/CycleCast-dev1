# AGENTS.md

> **Standard:** [agents.md](https://agents.md) | **Version:** 3.2 Final
>
> This file follows the open standard for AI coding agents and is compatible with:
> Claude, GPT-4/Codex, Gemini, Qwen, Cursor, Copilot, Windsurf, VS Code, and more.

---

## Project Overview

**CycleCast v3.2 Final** — A production-ready financial market cycle analysis and forecasting system based on **Larry Williams' methodology**.

| Market | Data | Special Features |
|--------|------|------------------|
| **TradFi** | 30-50 years OHLC | COT reports from CFTC |
| **Crypto** | 10-15 years | GBTC/ETF proxy for institutional analysis |

---

## Setup Commands

```bash
# Infrastructure (Docker)
docker-compose up -d

# Database migrations
make migrate-up

# Backend (Go API)
make run-api

# Python Quant (gRPC)
cd quant && python main.py

# Frontend (React)
cd frontend && bun dev

# Tests
make test
```

---

## Code Style

### Go (Backend)
- Use `gofmt` and `goimports`
- Error handling: wrap with context
- Service pattern: `*_service.go`, `*_repository.go`
- Interfaces for dependencies

### Python (Quant)
- Python 3.11+ with type hints
- Follow PEP 8
- NumPy/SciPy for math
- Use `black` formatter

### TypeScript (Frontend)
- Strict mode enabled
- Single quotes, no semicolons
- Functional React components
- Zustand for state, TanStack Query for server state

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   Web SPA (React)  │  Desktop (Electron)  │  CLI (Go)       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      GATEWAY LAYER                           │
│   REST API (Gin)  │  gRPC  │  WebSocket  │  HashiCorp Vault │
└─────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
┌─────────────────────┐           ┌─────────────────────┐
│    GO BACKEND       │   gRPC    │   PYTHON QUANT      │
│    (Core)           │ ◄───────► │   (Math/ML)         │
└─────────────────────┘           └─────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│   PostgreSQL 16 + TimescaleDB  │  Redis 7  │  Vault        │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Files

| Purpose | Path |
|---------|------|
| API server entry | `backend/cmd/api/main.go` |
| Python gRPC server | `quant/main.py` |
| Frontend entry | `frontend/src/app/page.tsx` |
| gRPC proto | `quant/proto/quant.proto` |
| DB migrations | `database/migrations/` |
| Config | `configs/config.yaml` |

---

## Key Algorithms

### QSpectrum (NOT FFT!)
```
C(period) = Σ P(t) × P(t-period) / (N - period)
E(period) = |C(period)| × √(N/period) × WFA_Stability
```

### FTE Adaptive Threshold
```
threshold = base × (1 + λ × (current_vol / long_term_vol - 1))
base = 0.05 (TradFi) or 0.08 (Crypto)
```

### Signal Decay
```
Effective_Strength = Initial × 0.5^(AgeDays / HalfLifeDays)
HalfLifeDays = 14
```

---

## Important Rules

### ⚠️ No Backtest = No Signal
Every strategy MUST pass:
- In-Sample / Out-of-Sample split (70/30)
- Bootstrap CI > 0 (95% confidence)
- p-value < 0.05
- Chow Test for structural breaks

### GBTC Proxy for Crypto
- `signal_direction = -1` (inverse!)
- `regime_change_date = 2024-01-11` (ETF conversion)
- Minimum autocorrelation filter: 21 days

---

## 🤖 Agent Workflow (REQUIRED)

### Start of Session:
1. **Read [WORKLOG.md](WORKLOG.md)** → Check last entry for "What to do next"
2. **Read [docs/TZ.md](docs/TZ.md)** → Understand requirements
3. **Read [docs/PLAN.md](docs/PLAN.md)** → Find current phase and Task ID
4. **Start working**

### End of Session:
1. **Add entry to WORKLOG.md** (at the top of history)
2. **Update status table** in WORKLOG.md
3. **Specify "What to do next"** for next agent
4. **Link to documentation sections** you worked with

### Entry Format:
```markdown
---
**Task ID:** [From PLAN.md]
**Agent:** [Your name: Claude, GPT-4, Kimi, Qwen...]
**Date:** [YYYY-MM-DD HH:MM]
**Duration:** [Time spent]

## Что сделано
- [x] Completed task
- [ ] Incomplete task

## Изменённые файлы
- `path/to/file` - description

## Что делать дальше
1. Next task for next agent

## Связь с документацией
- **TZ:** Section X.X
- **PLAN:** Phase N, Week M
- **TECHNICAL_SOLUTION:** Section X.X
```

---

## Documentation

| File | Purpose |
|------|---------|
| [docs/TZ.md](docs/TZ.md) | Technical specification |
| [docs/PLAN.md](docs/PLAN.md) | Development plan (44 weeks) |
| [docs/API.md](docs/API.md) | REST/gRPC API spec |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | ER diagram, SQL schemas |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | Code style guide |
| [docs/SECURITY.md](docs/SECURITY.md) | Auth, JWT, Vault, RBAC |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Terminology |

---

## Current Status

| Component | Status | Phase |
|-----------|--------|-------|
| Backend (Go) | Not started | Phase 1 |
| Python Quant | Not started | Phase 0 |
| Frontend | Not started | Phase 10 |
| Database | Not started | Phase 1 |

**Next Step:** Phase 0 - Backtesting & Math Prototyping

---

## Error Codes

| Code | Module | Description |
|------|--------|-------------|
| MD001-MD010 | Market Data | Data import/validation errors |
| AC001-AC008 | Annual Cycle | Seasonality errors |
| QS001-QS006 | QSpectrum | Cycle analysis errors |
| CO001-CO005 | COT/GBTC | Institutional data errors |

See [docs/ERRORS.md](docs/ERRORS.md) for full list.

---

## Test Strategy

```bash
# Unit tests
make test

# Integration tests
make test-integration

# Load testing
k6 run tests/load/api_load.js

# Chaos engineering
make chaos-test
```

---

_This file follows the [AGENTS.md specification](https://agents.md) for AI coding agent compatibility._
