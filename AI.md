# AI.md - Quick Reference для ИИ Агентов

> **Версия:** 3.2 Final | **Обновлено:** 2026-03-12
> 
> **Для:** Claude, GPT-4, Kimi K2.5, Qwen 3.5 Plus, и других ИИ-агентов

---

## 🚀 АЛГОРИТМ РАБОТЫ ИИ АГЕНТА

```
1. Прочитать WORKLOG.md — что сделано и что делать дальше
2. Прочитать AI.md (этот файл) — общая карта проекта
3. Прочитать docs/TZ.md — понять требования (ЧТО строим)
4. Прочитать docs/PLAN.md — понять этапы (КАКУЮ фазу)
5. Прочитать docs/API.md — понять endpoints
6. Прочитать docs/DATABASE_SCHEMA.md — понять таблицы
7. Выполнить задачу
8. ОБЯЗАТЕЛЬНО: добавить запись в WORKLOG.md
```

> ⚠️ **ВАЖНО:** В конце сессии ДОБАВИТЬ ЗАПИСЬ в [WORKLOG.md](WORKLOG.md) — что сделано и что делать дальше!

---

## 📚 ДОКУМЕНТАЦИЯ (Начинай отсюда!)

### Критически важные файлы

| Файл | Назначение | Когда читать |
|------|------------|--------------|
| **[docs/TZ.md](docs/TZ.md)** | Техническое задание | Понять ЧТО строим |
| **[docs/PLAN.md](docs/PLAN.md)** | План разработки (44 недели) | Понять ЭТАПЫ и сроки |
| **[docs/TECHNICAL_SOLUTION.md](docs/TECHNICAL_SOLUTION.md)** | Техническое решение | Понять КАК строим |

### Спецификации для разработки

| Файл | Назначение | Когда читать |
|------|------------|--------------|
| **[docs/API.md](docs/API.md)** | REST/gRPC API спецификация | Создавать endpoints |
| **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** | ER-диаграмма, SQL схемы | Создавать таблицы |
| **[docs/CONVENTIONS.md](docs/CONVENTIONS.md)** | Код-стайл, naming | Писать код |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Auth, JWT, Vault | Реализовывать безопасность |

### Вспомогательные файлы

| Файл | Назначение |
|------|------------|
| **[docs/GLOSSARY.md](docs/GLOSSARY.md)** | Глоссарий терминов (FTE, QSpectrum, COT...) |
| **[docs/ERRORS.md](docs/ERRORS.md)** | Коды ошибок (MD001, AC002, QS001...) |
| **[docs/TESTING.md](docs/TESTING.md)** | Стратегия тестирования |
| **[docs/MOCK_DATA.md](docs/MOCK_DATA.md)** | Тестовые данные |
| **[docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md)** | Полная структура проекта |

### Конфигурация

| Файл | Назначение |
|------|------------|
| **[.env.example](.env.example)** | Шаблон переменных окружения |
| **[Makefile](Makefile)** | Команды сборки и разработки |
| **[docker-compose.yml](docker-compose.yml)** | Локальная инфраструктура |

---

## 🗺️ КАРТА ПРОЕКТА (Top-Level)

```
cyclecast/
├── frontend/          # React Web Application (TypeScript)
├── backend/           # Go Core API Server
├── quant/             # Python Math/ML Services
├── infrastructure/    # Docker, K8s, Terraform
├── database/          # Migrations, Schemas, Seeds
├── docs/              # 📚 Документация проекта (см. выше)
├── scripts/           # Utility scripts
└── configs/           # Конфигурации (YAML, ENV)
```

---

## 📂 ДЕТАЛЬНАЯ СТРУКТУРА

### frontend/ (React + TypeScript)
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui primitives
│   │   ├── charts/             # Lightweight Charts wrappers
│   │   ├── dashboard/          # Dashboard widgets
│   │   ├── analysis/           # Analysis panels
│   │   └── backtest/           # Backtest visualisation
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utilities, API clients
│   ├── stores/                 # Zustand stores
│   ├── types/                  # TypeScript types
│   └── styles/                 # Tailwind, global CSS
├── public/                     # Static assets
└── tests/                      # Frontend tests
```

### backend/ (Go)
```
backend/
├── cmd/                        # Entry points
│   ├── api/                    # API server main
│   ├── worker/                 # Background worker main
│   └── cli/                    # CLI tools main
├── internal/                   # Private packages
│   ├── domain/                 # Domain models
│   ├── service/                # Business logic
│   │   ├── marketdata/
│   │   ├── seasonality/
│   │   ├── cycle/
│   │   ├── cot/
│   │   ├── risk/
│   │   ├── backtest/
│   │   ├── lineage/
│   │   └── workflow/
│   ├── repository/             # Data access
│   └── transport/              # API handlers (REST, gRPC, WS)
├── pkg/                        # Public packages
└── tests/                      # Backend tests
```

### quant/ (Python)
```
quant/
├── qspectrum/                  # Циклическая корреляция + MEM
├── phenom/                     # DTW гибридный
├── wfa/                        # Walk-Forward Analysis
├── bootstrap/                  # Bootstrap CI (streaming)
├── chow_test/                  # Structural break detection
├── shared/                     # Shared utilities
├── proto/                      # gRPC protobuf definitions
├── tests/
└── main.py                     # gRPC server entry
```

---

## 🔑 КЛЮЧЕВЫЕ ФАЙЛЫ (Quick Access)

| Назначение | Путь |
|------------|------|
| **API сервер** | `backend/cmd/api/main.go` |
| **Python gRPC** | `quant/main.py` |
| **Frontend entry** | `frontend/src/app/page.tsx` |
| **gRPC proto** | `quant/proto/quant.proto` |
| **DB migrations** | `database/migrations/` |
| **Config** | `configs/config.yaml` |

---

## 📝 КОНВЕНЦИИ (кратко)

| Тип | Pattern | Пример |
|-----|---------|--------|
| Go service | `*_service.go` | `marketdata_service.go` |
| Go repository | `*_repository.go` | `signal_repository.go` |
| React component | `PascalCase.tsx` | `CompositeLineChart.tsx` |
| React hook | `use*.ts` | `useAnnualCycle.ts` |
| Python module | `snake_case.py` | `burg_mem.py` |
| Test (Go) | `*_test.go` | `backdate_test.go` |

**Подробнее:** [docs/CONVENTIONS.md](docs/CONVENTIONS.md)

---

## ⚡ COMMANDS

```bash
# Backend
make run-api          # Запуск API сервера
make test             # Тесты
make migrate-up       # Миграции БД

# Frontend
cd frontend && bun dev

# Python Quant
cd quant && python main.py

# Docker (полная инфраструктура)
docker-compose up -d
```

---

## 📊 ТЕКУЩИЙ СТАТУС

| Компонент | Статус | Фаза |
|-----------|--------|------|
| Backend (Go) | Не начат | Phase 1 |
| Python Quant | Не начат | Phase 0 |
| Frontend | Не начат | Phase 10 |
| Database | Не начат | Phase 1 |
| Infrastructure | Не начат | Phase 1 |

**Следующий шаг:** Phase 0 - Backtesting & Math Prototyping

---

## 🎯 ПРОЕКТ В ОДНОМ АБЗАЦЕ

**CycleCast v3.2 Final** — система циклического анализа финансовых рынков по методологии Ларри Вильямса. 
- **TradFi**: 30-50 лет данных, COT отчёты CFTC
- **Crypto**: 10-15 лет, GBTC/ETF proxy
- **Стек**: Go backend, Python quant (NumPy/SciPy), React frontend, PostgreSQL + TimescaleDB
- **Методы**: Annual Cycle, QSpectrum (MEM, НЕ FFT), Composite Line, COT/GBTC Analysis, Backtesting с Bootstrap CI

---

_Этот файл оптимизирован для всех ИИ-агентов с ограниченным контекстом._
