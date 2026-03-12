# CycleCast v3.2 Final

## Система циклического анализа и прогнозирования финансовых рынков
### Методология Ларри Вильямса

---

> 🤖 **Для ИИ агентов:**
> - **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** — 🚨 PROTOCOL (ОБЯЗАТЕЛЬНО прочитать)
> - **[HANDSHAKE.md](./HANDSHAKE.md)** — 🤝 Регистрация сессий
> - **[WORKLOG.md](./WORKLOG.md)** — 📋 Журнал работы (что сделано / что делать дальше)
> - **[session.yaml](./session.yaml)** — 🔒 Активные сессии и блокировки
> - **[tasks.yaml](./tasks.yaml)** — 📝 Очередь задач
> - **[AGENTS.md](./AGENTS.md)** — открытый стандарт (OpenAI, Claude, Gemini, Qwen...)

---

## 📚 Документация проекта

### Критически важные файлы

| Файл | Назначение |
|------|------------|
| **[docs/TZ.md](docs/TZ.md)** | Техническое задание v3.2 Final |
| **[docs/PLAN.md](docs/PLAN.md)** | План разработки (44 недели, 11 фаз) |
| **[docs/TECHNICAL_SOLUTION.md](docs/TECHNICAL_SOLUTION.md)** | Техническое решение (архитектура) |

### Спецификации для разработки

| Файл | Назначение |
|------|------------|
| **[docs/API.md](docs/API.md)** | REST/gRPC API спецификация (endpoints, request/response) |
| **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** | ER-диаграмма, SQL схемы всех таблиц |
| **[docs/CONVENTIONS.md](docs/CONVENTIONS.md)** | Код-стайл (Go, Python, TypeScript, SQL) |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Auth, JWT, Vault, RBAC, TLS |

### Вспомогательные файлы

| Файл | Назначение |
|------|------------|
| **[docs/GLOSSARY.md](docs/GLOSSARY.md)** | Глоссарий терминов (FTE, QSpectrum, COT, GBTC Index...) |
| **[docs/ERRORS.md](docs/ERRORS.md)** | Коды ошибок по модулям (MD001, AC001, QS001...) |
| **[docs/TESTING.md](docs/TESTING.md)** | Стратегия тестирования, примеры |
| **[docs/MOCK_DATA.md](docs/MOCK_DATA.md)** | Тестовые данные, seed scripts |
| **[docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md)** | Полная структура проекта |

### Конфигурация

| Файл | Назначение |
|------|------------|
| **[Makefile](Makefile)** | Команды разработки (`make run`, `make test`) |
| **[docker-compose.yml](docker-compose.yml)** | Локальная инфраструктура |
| **[.env.example](.env.example)** | Шаблон переменных окружения |

---

<p align="center">
  <a href="#-методология-ларри-вильямса">Методология</a> •
  <a href="#-компоненты">Компоненты</a> •
  <a href="#-архитектура">Архитектура</a> •
  <a href="#-установка">Установка</a> •
  <a href="#-api">API</a>
</p>

---

## 📋 Описание

**CycleCast v3.2 Final** — это production-ready система институционального уровня для моделирования и прогнозирования поведения финансовых рынков, основанная на **методологии Ларри Вильямса**:

### Поддерживаемые рынки

| Сегмент | Активы | Данные |
|---------|--------|--------|
| **TradFi** | Акции, фьючерсы, форекс, индексы | 30-50 лет, COT отчёты CFTC |
| **Crypto** | Биткоин, альткоины | 10-15 лет, GBTC/ETF proxy |
| **Hybrid** | Смешанные портфели | Агрегация сигналов |

### Основные возможности

- **Annual Cycle / Seasonality** — Сезонный анализ с адаптивным FTE порогом
- **QSpectrum** — Циклическая корреляция + МЭМ (НЕ FFT!)
- **Composite Line** — Композитная линия прогноза (3 цикла, резонанс)
- **Decennial Patterns** — Десятилетние паттерны (годы 0-9)
- **Phenomenological Model** — Исторические аналогии (DTW гибридный)
- **COT/GBTC Analysis** — Анализ "умных денег" (Percentile Rank, Autocorrelation Filter)
- **Risk Management** — Position Sizing, Stop-Loss, Signal Decay
- **Backtesting Engine** — Симуляция на истории, Bootstrap CI (streaming)
- **Statistical Validation** — p-value, доверительные интервалы, Chow Test
- **Data Lineage** — Audit trail для compliance (SEC/CFTC ready)

---

## 🎯 Методология Ларри Вильямса

### Пошаговый алгоритм (v3.2)

```
Шаг 0: Backtesting Engine → Валидация на истории (ОБЯЗАТЕЛЬНО)
Шаг 1: Сезонность (Annual Cycle) → "ЧТО торговать?"
Шаг 2: Циклы (Composite Line) → "КОГДА входить?"
Шаг 3: Исторические аналогии (Phenomenological) → Проверка
Шаг 4: COT/GBTC → Подтверждение "Умными деньгами"
Шаг 5: Risk Management → Расчёт позиции
Шаг 6: Qualified Trend Break → Точка входа
Шаг 7: Statistical Validation → p-value, Bootstrap CI
Шаг 8: Data Lineage → Audit trail для compliance
```

### Ключевой принцип

> Ларри Вильямс **не ищет один идеальный цикл**. Он накладывает **три волны разной длины** (короткий, средний, длинный цикл) и ищет точки **"резонанса"** — когда все три цикла направлены в одну сторону.

---

## ✨ Компоненты

### 🔬 Методы анализа

| Компонент | Назначение | Технология |
|-----------|------------|------------|
| **Annual Cycle** | Сезонные тренды | Go, 30-50 лет OHLC |
| **FTE** | Валидация сезонности | Адаптивный порог (realised volatility) |
| **QSpectrum** | Циклическая корреляция | **Python**, Burg's MEM |
| **Composite Line** | Прогнозная линия | 3 цикла, резонанс BUY/SELL |
| **Phenomenological** | Исторические аналогии | **Python**, DTW гибридный |
| **U-Turn** | Разворотные точки | Go |
| **COT/GBTC** | Позиции хеджеров / Premium | Percentile Rank, Autocorrelation Filter |
| **Risk Management** | Позиция, Stop-Loss | Signal Decay |
| **Backtesting** | Валидация стратегии | Bootstrap CI (streaming) |
| **Data Lineage** | Audit trail | Compliance-ready |

### 📊 GBTC/ETF Proxy для криптовалют

```
Для биткоина вместо COT используется GBTC Premium:

1. Загрузить данные GBTC (цена, NAV)
2. Рассчитать премию: Premium = (Price - NAV) / NAV × 100%
3. Применить regime_change_date (только после 2024-01-11)
4. Рассчитать Percentile Rank за 26 недель
5. Интерпретировать с signal_direction = -1 (инверсия!)
6. Фильтр автокорреляции (min 21 день)
7. Взвешенная агрегация нескольких прокси (GBTC + IBIT + FBTC)
```

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   Web SPA (React)  │  Desktop (Electron)  │  CLI (Go)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
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
│    - MarketData     │           │   - QSpectrum       │
│    - AnnualCycle    │           │   - Phenom (DTW)    │
│    - COT/GBTC       │           │   - Bootstrap CI    │
│    - Risk           │           │   - Chow Test       │
│    - Backtest       │           │                     │
│    - Lineage        │           │                     │
└─────────────────────┘           └─────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│   PostgreSQL 16 + TimescaleDB  │  Redis 7  │  Vault        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Технологический стек

| Компонент | Технология |
|-----------|------------|
| **Backend (Core)** | Go 1.22+ |
| **Python Quant** | Python 3.11+, NumPy, SciPy, Statsmodels |
| **Frontend** | React 18 + TypeScript + Vite |
| **Database** | PostgreSQL 16 + TimescaleDB |
| **Cache** | Redis 7 |
| **API** | REST (Gin) + gRPC (streaming) |
| **Secrets** | HashiCorp Vault |
| **Charts** | Lightweight Charts |
| **Monitoring** | Prometheus + Grafana |
| **Containerization** | Docker + Docker Compose |

---

## 📦 Установка

### Требования

- Go 1.22+
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (для frontend)

### Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/nix0902/CycleCast.git
cd CycleCast

# Запуск инфраструктуры
docker-compose up -d

# Применение миграций
make migrate-up

# Запуск API сервера
make run-api
```

---

## 🔬 Алгоритмы

### QSpectrum (Циклическая корреляция + МЭМ)

> **Важно:** QSpectrum **НЕ использует FFT**!
> Разработан специально для нестационарных финансовых данных.

```
Методы QSpectrum:

1. Циклическая корреляция (основной):
   C(period) = Σ P(t) × P(t-period) / (N - period)

2. Энергия цикла:
   E(period) = |C(period)| × √(N/period) × WFA_Stability

3. МЭМ — спектральная плотность (Burg's method):
   P(f) = σ² / |1 + Σ aₖ × e^(-i2πfk)|²

4. Walk-Forward Stability:
   WFA_Stability = Count(Correlation > 0) / Total_Periods
```

### FTE Адаптивный порог

```
threshold = base × (1 + λ × (current_vol / long_term_vol - 1))

где:
- base = 0.05 (TradFi) или 0.08 (Crypto)
- λ = 0.5 (sensitivity parameter)
```

### GBTC Index (Percentile Rank)

```
GBTC_Index = PercentileRank(Current_Premium, Window_N)

Сигналы (signal_direction = -1):
- GBTC_Index > 80: BEARISH (эйфория, институты продают)
- GBTC_Index < 20: BULLISH (паника, институты покупают)
```

### Signal Decay

```
Effective_Strength = Initial × 0.5^(AgeDays / HalfLifeDays)
HalfLifeDays = 14 (по умолчанию)
```

### Bootstrap CI (95%, streaming)

```
Для n итераций (обычно 1000):
1. Resample returns с заменой
2. Рассчитать метрику
3. CI = [P_2.5, P_97.5]

Streaming через gRPC для прогресса.
```

---

## 📖 API Documentation

### REST API

| Method | Endpoint | Описание |
|--------|----------|----------|
| `POST` | `/api/v1/market/import` | Импорт данных |
| `GET` | `/api/v1/market/history` | Исторические данные |
| `POST` | `/api/v1/analysis/annual-cycle` | Annual Cycle анализ |
| `POST` | `/api/v1/analysis/qspectrum` | QSpectrum анализ |
| `POST` | `/api/v1/analysis/composite` | Composite Line |
| `POST` | `/api/v1/cot/gbtc` | GBTC Index |
| `POST` | `/api/v1/backtest/run` | Запуск бэктеста |
| `POST` | `/api/v1/risk/calculate` | Расчёт позиции |
| `POST` | `/api/v1/workflow/williams` | Полный workflow |
| `GET` | `/api/v1/lineage/{signal_id}` | Data Lineage |

### gRPC (Python Quant)

```protobuf
service QuantService {
    rpc QSpectrum(QSpectrumRequest) returns (QSpectrumResponse);
    rpc PhenomSearch(PhenomRequest) returns (PhenomResponse);
    rpc Bootstrap(BootstrapRequest) returns (stream BootstrapProgress);
    rpc ChowTest(ChowTestRequest) returns (ChowTestResponse);
}
```

---

## 📊 Примеры результатов

### QSpectrum Result

```json
{
  "cycles": [
    {"period": 14, "energy": 0.85, "stability": 0.72},
    {"period": 28, "energy": 0.72, "stability": 0.65},
    {"period": 56, "energy": 0.61, "stability": 0.58}
  ],
  "top3": [...],
  "spectrum": [...]
}
```

### Backtest Result с Bootstrap CI

```json
{
  "total_return": 45.2,
  "sharpe_ratio": 1.35,
  "max_drawdown": 18.5,
  "win_rate": 0.52,
  "p_value": 0.03,
  "bootstrap_ci_lower": 12.5,
  "bootstrap_ci_upper": 78.3
}
```

### Data Lineage

```json
{
  "signal_id": "uuid",
  "source_data": [
    {"type": "market_data", "id": "uuid", "hash": "sha256..."},
    {"type": "cot_data", "id": "uuid", "hash": "sha256..."}
  ],
  "transformations": [
    {"name": "annual_cycle", "version": "v1.2.3", "input_hash": "...", "output_hash": "..."}
  ],
  "code_version": "abc123def",
  "timestamp": "2026-03-12T10:00:00Z",
  "checksum": "sha256..."
}
```

---

## 📁 Структура проекта

```
cyclecast/
├── cmd/                    # Точки входа
├── internal/               # Внутренние пакеты
│   ├── domain/            # Доменные модели
│   ├── service/           # Бизнес-логика
│   │   ├── marketdata/    # Market Data
│   │   ├── seasonality/   # Annual Cycle, FTE
│   │   ├── cot/           # COT + GBTC адаптация
│   │   ├── risk/          # Risk Management
│   │   ├── backtest/      # Backtesting Engine
│   │   └── lineage/       # Data Lineage
│   └── transport/         # API handlers
├── quant/                  # Python Quant (Math/ML)
│   ├── qspectrum/         # Burg's MEM
│   ├── phenom/            # DTW гибридный
│   └── bootstrap/         # Bootstrap CI (streaming)
├── docs/                   # Документация
│   ├── PLAN.md            # План разработки (44 недели)
│   ├── TZ.md              # Техническое задание
│   └── TECHNICAL_SOLUTION.md
└── web/                    # Frontend
```

---

## 🧪 Тестирование

```bash
# Unit тесты
make test

# Backtest валидация
make backtest-validate

# Load testing
k6 run tests/load/api_load.js

# Chaos Engineering
make chaos-test
```

---

## ⚠️ Правило бэктеста

```
⚠️ НЕТ БЭКТЕСТА → НЕТ СИГНАЛА В ПРОДАКШЕНЕ
```

Каждая стратегия должна пройти:
- In-Sample / Out-of-Sample разделение (70/30)
- Bootstrap CI > 0 (95% confidence)
- p-value < 0.05
- Chow Test для структурных сдвигов

---

## 🔒 Compliance

### Data Lineage
- Полная traceability каждого сигнала
- Версия кода (git commit)
- Исходные данные (hash)
- Параметры моделей

### Audit Logging
- Все действия пользователей логируются
- Изменения конфигурации трекаются
- Доступ к API-ключам аудитится

### Chaos Engineering
| ID | Сценарий | Критерий |
|----|----------|----------|
| CT-001 | Python service failure | Go degrades gracefully |
| CT-002 | Redis failure | Fallback to PostgreSQL |
| CT-003 | API load spike | Rate limiting activates |
| CT-004 | Database latency | Circuit breaker opens |
| CT-005 | Network partition | gRPC retry logic works |

---

## 📄 Лицензия

MIT License. См. [LICENSE](LICENSE) для деталей.

---

## ⚠️ Disclaimer

**ВАЖНО**: Данная система предназначена исключительно для исследовательских и образовательных целей. Прошлые результаты не гарантируют будущих доходов. Любые торговые решения принимаются на ваш собственный риск.

---

## 📞 Контакты

- **Issues**: [GitHub Issues](https://github.com/nix0902/CycleCast/issues)

---

<p align="center">
  <b>CycleCast v3.2 Final</b> — Циклический анализ по методологии Ларри Вильямса
</p>
