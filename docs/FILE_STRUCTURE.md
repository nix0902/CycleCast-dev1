# FILE_STRUCTURE.md - Полная Структура Проекта

> **Версия:** 3.2 Final | **Проект:** CycleCast | **Обновлено:** 2026-03-12

---

## 📁 КОРНЕВАЯ СТРУКТУРА

```
cyclecast/
├── frontend/                    # React Web Application
├── backend/                     # Go Core API Server  
├── quant/                       # Python Math/ML Services
├── infrastructure/              # DevOps & Deployment
├── database/                    # Database Layer
├── docs/                        # Project Documentation
├── scripts/                     # Utility Scripts
├── configs/                     # Configuration Files
├── AGENTS.md                    # Open standard for AI agents
├── AGENT_INSTRUCTIONS.md        # Strict protocol for AI agents (MUST READ)
├── HANDSHAKE.md                 # Agent registration and session protocol
├── AUTO_ASSIGNMENT.md           # Automatic task assignment
├── QUALITY_GATE.md              # Second agent review system
├── WORKLOG.md                   # Agent work log
├── session.yaml                 # Active sessions and locks
├── tasks.yaml                   # Machine-readable task queue
├── quality_gate.yaml            # Review queue and history
├── agent_skills.yaml            # Agent skills and preferences
├── progress.yaml                # Current project progress
├── AI.md                        # Universal AI Agent Quick Reference
├── CLAUDE.md                    # Redirect to AI.md
├── README.md                    # Project Overview
├── Makefile                     # Build Commands
├── docker-compose.yml           # Local Development
└── .gitignore
```

---

## 🎨 FRONTEND (React + TypeScript + Next.js)

```
frontend/
├── src/
│   ├── app/                           # Next.js 16 App Router
│   │   ├── layout.tsx                 # Root layout
│   │   ├── page.tsx                   # Home page (/)
│   │   ├── globals.css                # Global styles
│   │   ├── dashboard/
│   │   │   └── page.tsx               # /dashboard
│   │   ├── analysis/
│   │   │   ├── page.tsx               # /analysis
│   │   │   ├── annual-cycle/
│   │   │   │   └── page.tsx           # /analysis/annual-cycle
│   │   │   ├── qspectrum/
│   │   │   │   └── page.tsx           # /analysis/qspectrum
│   │   │   ├── composite/
│   │   │   │   └── page.tsx           # /analysis/composite
│   │   │   ├── phenom/
│   │   │   │   └── page.tsx           # /analysis/phenom
│   │   │   └── cot/
│   │   │       └── page.tsx           # /analysis/cot
│   │   ├── backtest/
│   │   │   └── page.tsx               # /backtest
│   │   ├── signals/
│   │   │   └── page.tsx               # /signals
│   │   ├── settings/
│   │   │   └── page.tsx               # /settings
│   │   └── api/                       # Next.js API routes
│   │       └── v1/
│   │           └── [...]/
│   │
│   ├── components/                    # React Components
│   │   ├── ui/                        # shadcn/ui primitives
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── form.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/                    # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Navigation.tsx
│   │   │
│   │   ├── charts/                    # Chart components
│   │   │   ├── OHLCChart.tsx          # Lightweight Charts
│   │   │   ├── CompositeLineChart.tsx
│   │   │   ├── AnnualCycleChart.tsx
│   │   │   ├── SpectrumChart.tsx
│   │   │   ├── COTChart.tsx
│   │   │   ├── EquityCurveChart.tsx
│   │   │   └── ProjectionChart.tsx
│   │   │
│   │   ├── dashboard/                 # Dashboard widgets
│   │   │   ├── ActiveAssetsWidget.tsx
│   │   │   ├── SignalsWidget.tsx
│   │   │   ├── COTStatusWidget.tsx
│   │   │   ├── PerformanceWidget.tsx
│   │   │   └── AlertsWidget.tsx
│   │   │
│   │   ├── analysis/                  # Analysis panels
│   │   │   ├── AnnualCyclePanel.tsx
│   │   │   ├── QSpectrumPanel.tsx
│   │   │   ├── CompositePanel.tsx
│   │   │   ├── PhenomPanel.tsx
│   │   │   ├── COTPanel.tsx
│   │   │   ├── RiskPanel.tsx
│   │   │   └── ParametersForm.tsx
│   │   │
│   │   ├── backtest/                  # Backtest components
│   │   │   ├── BacktestForm.tsx
│   │   │   ├── BacktestResults.tsx
│   │   │   ├── MetricsTable.tsx
│   │   │   ├── BootstrapCIChart.tsx
│   │   │   └── TradeHistory.tsx
│   │   │
│   │   ├── signals/                   # Signal components
│   │   │   ├── SignalCard.tsx
│   │   │   ├── SignalList.tsx
│   │   │   ├── SignalDetail.tsx
│   │   │   └── SignalFilters.tsx
│   │   │
│   │   ├── lineage/                   # Data Lineage
│   │   │   ├── LineageViewer.tsx
│   │   │   ├── LineageGraph.tsx
│   │   │   └── LineageExport.tsx
│   │   │
│   │   └── common/                    # Shared components
│   │       ├── Loading.tsx
│   │       ├── ErrorBoundary.tsx
│   │       ├── DateRangePicker.tsx
│   │       ├── SymbolSelector.tsx
│   │       └── StatusBadge.tsx
│   │
│   ├── hooks/                         # Custom React Hooks
│   │   ├── useAnnualCycle.ts
│   │   ├── useQSpectrum.ts
│   │   ├── useComposite.ts
│   │   ├── usePhenom.ts
│   │   ├── useCOT.ts
│   │   ├── useBacktest.ts
│   │   ├── useSignals.ts
│   │   ├── useLineage.ts
│   │   ├── useMarketData.ts
│   │   ├── useWebSocket.ts
│   │   └── useToast.ts
│   │
│   ├── lib/                           # Utilities
│   │   ├── api/                       # API clients
│   │   │   ├── client.ts              # Base fetch client
│   │   │   ├── marketdata.ts
│   │   │   ├── analysis.ts
│   │   │   ├── cot.ts
│   │   │   ├── backtest.ts
│   │   │   ├── signals.ts
│   │   │   └── lineage.ts
│   │   ├── utils.ts                   # Utility functions
│   │   ├── date.ts                    # Date utilities
│   │   ├── math.ts                    # Math utilities
│   │   ├── validation.ts              # Form validation
│   │   └── constants.ts               # App constants
│   │
│   ├── stores/                        # Zustand State Management
│   │   ├── useAppStore.ts
│   │   ├── useAuthStore.ts
│   │   ├── useAnalysisStore.ts
│   │   ├── useBacktestStore.ts
│   │   └── useSettingsStore.ts
│   │
│   ├── types/                         # TypeScript Types
│   │   ├── api.ts
│   │   ├── marketdata.ts
│   │   ├── analysis.ts
│   │   ├── cot.ts
│   │   ├── backtest.ts
│   │   ├── signals.ts
│   │   ├── lineage.ts
│   │   └── common.ts
│   │
│   └── styles/                        # Styling
│       ├── globals.css
│       ├── themes/
│       │   ├── light.css
│       │   └── dark.css
│       └── animations.css
│
├── public/                            # Static Assets
│   ├── favicon.ico
│   ├── logo.svg
│   ├── images/
│   └── fonts/
│
├── tests/                             # Frontend Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── postcss.config.mjs
└── .env.local
```

---

## 🔧 BACKEND (Go)

```
backend/
├── cmd/                               # Entry Points
│   ├── api/                           # API Server
│   │   └── main.go
│   ├── worker/                        # Background Worker
│   │   └── main.go
│   └── cli/                           # CLI Tools
│       └── main.go
│
├── internal/                          # Private Packages
│   ├── domain/                        # Domain Models
│   │   ├── marketdata.go
│   │   ├── instrument.go
│   │   ├── annual_cycle.go
│   │   ├── cycle.go
│   │   ├── composite_line.go
│   │   ├── cot.go
│   │   ├── signal.go
│   │   ├── backtest.go
│   │   ├── lineage.go
│   │   ├── risk.go
│   │   └── errors.go
│   │
│   ├── service/                       # Business Logic
│   │   ├── marketdata/                # Market Data Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── import.go
│   │   │   ├── providers/
│   │   │   │   ├── yahoo.go
│   │   │   │   ├── alphavantage.go
│   │   │   │   ├── coingecko.go
│   │   │   │   └── provider.go
│   │   │   ├── circuit_breaker.go
│   │   │   └── cache.go
│   │   │
│   │   ├── seasonality/               # Annual Cycle Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── annual_cycle.go
│   │   │   ├── fte.go
│   │   │   ├── decennial.go
│   │   │   └── adaptive_threshold.go
│   │   │
│   │   ├── cycle/                     # Cycle Analysis Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── qspectrum.go
│   │   │   ├── composite.go
│   │   │   ├── uturn.go
│   │   │   └── qtb.go
│   │   │
│   │   ├── phenom/                    # Phenomenological Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   └── dtw.go
│   │   │
│   │   ├── cot/                       # COT/GBTC Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── cot_analyzer.go
│   │   │   ├── gbtc_analyzer.go
│   │   │   ├── percentile_rank.go
│   │   │   ├── autocorrelation_filter.go
│   │   │   ├── liquidity_weighted.go
│   │   │   └── parsers/
│   │   │       ├── cftc.go
│   │   │       └── grayscale.go
│   │   │
│   │   ├── risk/                      # Risk Management Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── position_sizing.go
│   │   │   ├── stop_loss.go
│   │   │   ├── signal_decay.go
│   │   │   └── metrics.go
│   │   │
│   │   ├── backtest/                  # Backtest Engine
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── engine.go
│   │   │   ├── simulator.go
│   │   │   ├── metrics.go
│   │   │   ├── walk_forward.go
│   │   │   └── chow_test.go
│   │   │
│   │   ├── lineage/                   # Data Lineage Service
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── tracker.go
│   │   │   ├── audit.go
│   │   │   └── export.go
│   │   │
│   │   ├── statistics/                # Statistical Validation
│   │   │   ├── service.go
│   │   │   ├── service_impl.go
│   │   │   ├── bootstrap.go
│   │   │   └── significance.go
│   │   │
│   │   └── workflow/                  # Integration Workflow
│   │       ├── service.go
│   │       ├── service_impl.go
│   │       ├── williams_workflow.go
│   │       └── paper_trading.go
│   │
│   ├── repository/                    # Data Access Layer
│   │   ├── marketdata/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── instrument/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── cycle/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── cot/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── signal/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── backtest/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   ├── lineage/
│   │   │   ├── repository.go
│   │   │   └── repository_pg.go
│   │   └── cache/
│   │       ├── cache.go
│   │       └── cache_redis.go
│   │
│   ├── transport/                     # API Handlers
│   │   ├── rest/                      # REST API
│   │   │   ├── server.go
│   │   │   ├── routes.go
│   │   │   ├── middleware/
│   │   │   │   ├── auth.go
│   │   │   │   ├── rate_limit.go
│   │   │   │   ├── logging.go
│   │   │   │   └── cors.go
│   │   │   ├── handler/
│   │   │   │   ├── marketdata_handler.go
│   │   │   │   ├── analysis_handler.go
│   │   │   │   ├── cot_handler.go
│   │   │   │   ├── backtest_handler.go
│   │   │   │   ├── signal_handler.go
│   │   │   │   ├── lineage_handler.go
│   │   │   │   └── workflow_handler.go
│   │   │   └── response/
│   │   │       └── response.go
│   │   │
│   │   ├── grpc/                      # gRPC Server
│   │   │   ├── server.go
│   │   │   └── interceptors.go
│   │   │
│   │   └── ws/                        # WebSocket
│   │       ├── hub.go
│   │       ├── client.go
│   │       └── handler.go
│   │
│   └── pkg/                           # Internal Utilities
│       ├── config/
│       │   └── config.go
│       ├── logger/
│       │   └── logger.go
│       ├── crypto/
│       │   └── hash.go
│       ├── validation/
│       │   └── validator.go
│       └── quant_client/              # Python gRPC client
│           ├── client.go
│           └── proto/
│
├── pkg/                               # Public Packages
│   ├── models/                        # Shared models
│   └── utils/                         # Shared utilities
│
├── tests/                             # Tests
│   ├── unit/
│   ├── integration/
│   └── mocks/
│
├── go.mod
├── go.sum
├── Makefile
└── .env
```

---

## 🐍 QUANT (Python Math/ML Services)

```
quant/
├── qspectrum/                         # QSpectrum Module
│   ├── __init__.py
│   ├── core.py                        # Main QSpectrum logic
│   ├── cyclic_correlation.py          # Циклическая корреляция
│   ├── burg_mem.py                    # Burg's MEM implementation
│   ├── energy.py                      # Cycle energy calculation
│   ├── wfa.py                         # Walk-Forward Analysis
│   ├── selector.py                    # Top-3 cycle selection
│   └── test_core.py
│
├── phenom/                            # Phenomenological Module
│   ├── __init__.py
│   ├── core.py                        # Main Phenom logic
│   ├── dtw.py                         # Exact DTW implementation
│   ├── dtw_fast.py                    # FastDTW approximation
│   ├── hybrid.py                      # Hybrid DTW (filter + exact)
│   ├── decennial_filter.py            # YearDigit filtering
│   ├── ranking.py                     # Best matches ranking
│   ├── projection.py                  # Projection generation
│   └── test_core.py
│
├── wfa/                               # Walk-Forward Analysis
│   ├── __init__.py
│   ├── core.py
│   ├── stability.py
│   └── test_core.py
│
├── bootstrap/                         # Bootstrap CI (streaming)
│   ├── __init__.py
│   ├── core.py                        # Main Bootstrap logic
│   ├── streaming.py                   # Streaming implementation
│   ├── ci.py                          # Confidence intervals
│   ├── pvalue.py                      # P-value calculation
│   └── test_core.py
│
├── chow_test/                         # Structural Break Detection
│   ├── __init__.py
│   ├── core.py
│   ├── regime_detection.py
│   └── test_core.py
│
├── shared/                            # Shared Utilities
│   ├── __init__.py
│   ├── normalization.py               # Percentile Rank, etc.
│   ├── detrending.py                  # Detrending methods
│   ├── volatility.py                  # Realised volatility
│   ├── correlation.py                 # Pearson correlation
│   ├── cache.py                       # Redis caching
│   └── types.py                       # Type definitions
│
├── proto/                             # gRPC Protocol Buffers
│   ├── quant.proto                    # Proto definitions
│   ├── quant_pb2.py                   # Generated Python
│   └── quant_pb2_grpc.py              # Generated gRPC
│
├── config/                            # Configuration
│   ├── __init__.py
│   ├── settings.py
│   └── logging.py
│
├── tests/                             # Integration Tests
│   ├── test_grpc.py
│   └── fixtures/
│
├── main.py                            # gRPC Server Entry
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── .env
```

---

## 🏗️ INFRASTRUCTURE (DevOps)

```
infrastructure/
├── docker/                            # Docker Configuration
│   ├── Dockerfile.api                 # API server
│   ├── Dockerfile.worker              # Background worker
│   ├── Dockerfile.quant               # Python Quant service
│   ├── Dockerfile.frontend            # Frontend
│   ├── docker-compose.yml             # Local development
│   ├── docker-compose.prod.yml        # Production
│   └── .dockerignore
│
├── kubernetes/                        # Kubernetes Manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployments/
│   │   ├── api.yaml
│   │   ├── worker.yaml
│   │   ├── quant.yaml
│   │   └── frontend.yaml
│   ├── services/
│   │   ├── api.yaml
│   │   ├── quant.yaml
│   │   └── frontend.yaml
│   ├── ingress.yaml
│   └── hpa/
│       └── api-hpa.yaml
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── database/
│   │   ├── redis/
│   │   ├── vault/
│   │   └── monitoring/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
│
├── monitoring/                        # Monitoring Stack
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── alerts.yml
│   │   └── rules.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── api.json
│   │   │   ├── quant.json
│   │   │   └── business.json
│   │   └── datasources/
│   │       └── prometheus.yml
│   └── alertmanager/
│       └── config.yml
│
└── vault/                             # HashiCorp Vault
    ├── policies/
    │   ├── api.hcl
    │   └── quant.hcl
    └── scripts/
        └── setup.sh
```

---

## 🗄️ DATABASE

```
database/
├── migrations/                        # SQL Migrations
│   ├── 0001_initial_schema.up.sql
│   ├── 0001_initial_schema.down.sql
│   ├── 0002_instruments_table.up.sql
│   ├── 0002_instruments_table.down.sql
│   ├── 0003_market_data_table.up.sql
│   ├── 0003_market_data_table.down.sql
│   ├── 0004_timescaledb_setup.up.sql
│   ├── 0004_timescaledb_setup.down.sql
│   ├── 0005_cot_data_table.up.sql
│   ├── 0005_cot_data_table.down.sql
│   ├── 0006_signals_table.up.sql
│   ├── 0006_signals_table.down.sql
│   ├── 0007_backtest_results_table.up.sql
│   ├── 0007_backtest_results_table.down.sql
│   ├── 0008_data_lineage_table.up.sql
│   ├── 0008_data_lineage_table.down.sql
│   └── ...
│
├── schemas/                           # Schema Definitions
│   ├── instruments.sql
│   ├── market_data.sql
│   ├── cot_data.sql
│   ├── signals.sql
│   ├── backtest_results.sql
│   ├── data_lineage.sql
│   ├── cycles.sql
│   ├── composite_lines.sql
│   └── annual_cycles.sql
│
├── seeds/                             # Test/Dev Data
│   ├── instruments.sql
│   ├── sample_market_data.sql
│   └── sample_cot_data.sql
│
├── timescaledb/                       # TimescaleDB Setup
│   ├── hypertables.sql
│   ├── continuous_aggregates.sql
│   └── retention_policies.sql
│
└── scripts/
    ├── migrate.sh
    ├── seed.sh
    └── backup.sh
```

---

## 📚 DOCS (Documentation)

```
docs/
├── TZ.md                              # Техническое задание
├── PLAN.md                            # План разработки (44 недели)
├── TECHNICAL_SOLUTION.md              # Техническое решение
├── FILE_STRUCTURE.md                  # Этот файл
├── API.md                             # API документация
├── DEPLOYMENT.md                      # Инструкция деплоя
├── DEVELOPMENT.md                     # Guide для разработчиков
│
├── algorithms/                        # Алгоритмы
│   ├── annual_cycle.md
│   ├── qspectrum.md
│   ├── composite_line.md
│   ├── dtw.md
│   ├── cot_index.md
│   ├── gbtc_index.md
│   ├── risk_management.md
│   ├── backtest_engine.md
│   └── statistical_validation.md
│
├── architecture/                      # Архитектура
│   ├── overview.md
│   ├── go_backend.md
│   ├── python_quant.md
│   ├── frontend.md
│   ├── database.md
│   └── security.md
│
├── api/                               # API Specs
│   ├── openapi.yaml
│   └── proto/
│       └── quant.proto
│
└── diagrams/                          # Architecture Diagrams
    ├── system_architecture.png
    ├── data_flow.png
    └── deployment.png
```

---

## 📜 SCRIPTS (Utility Scripts)

```
scripts/
├── setup/                             # Setup Scripts
│   ├── dev_setup.sh
│   └── install_dependencies.sh
│
├── data/                              # Data Scripts
│   ├── import_historical.sh
│   ├── validate_data.sh
│   └── sync_cot.sh
│
├── build/                             # Build Scripts
│   ├── build_all.sh
│   ├── build_frontend.sh
│   └── build_backend.sh
│
├── test/                              # Test Scripts
│   ├── run_all_tests.sh
│   ├── run_chaos_tests.sh
│   └── run_load_tests.sh
│
└── deploy/                            # Deployment Scripts
    ├── deploy.sh
    ├── rollback.sh
    └── health_check.sh
```

---

## ⚙️ CONFIGS (Configuration Files)

```
configs/
├── config.yaml                        # Main config
├── config.dev.yaml                    # Development
├── config.staging.yaml                # Staging
├── config.prod.yaml                   # Production
│
├── api/
│   └── routes.yaml                    # API routes config
│
├── quant/
│   └── quant.yaml                     # Python Quant config
│
└── secrets/                           # Secrets templates
    ├── api.env.example
    ├── quant.env.example
    └── database.env.example
```

---

## 📊 СВОДНАЯ ТАБЛИЦА

| Layer | Directory | Technology | Purpose |
|-------|-----------|------------|---------|
| Frontend | `frontend/` | React, Next.js, TypeScript | Web UI |
| Backend | `backend/` | Go, Gin, gRPC | API Core |
| Quant | `quant/` | Python, NumPy, SciPy | Math/ML |
| Infrastructure | `infrastructure/` | Docker, K8s, Terraform | DevOps |
| Database | `database/` | PostgreSQL, TimescaleDB | Data |
| Docs | `docs/` | Markdown | Documentation |
| Scripts | `scripts/` | Bash, Python | Utilities |
| Configs | `configs/` | YAML, ENV | Configuration |

---

## 🚀 QUICK START PATH

```
1. infrastructure/docker/docker-compose.yml    # Запуск инфраструктуры
2. database/migrations/                        # Применение миграций
3. backend/cmd/api/main.go                     # Запуск API
4. quant/main.py                               # Запуск Python Quant
5. frontend/src/app/page.tsx                   # Открытие UI
```

---

_Этот документ содержит полную структуру проекта для быстрой навигации._
