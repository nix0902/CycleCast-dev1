# ТЕХНИЧЕСКОЕ РЕШЕНИЕ
## Система циклического анализа и прогнозирования финансовых рынков
### CycleCast v3.2 Final - Методология Ларри Вильямса

---

## 1. АРХИТЕКТУРА СИСТЕМЫ

### 1.1 Высокоуровневая архитектура
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    PRESENTATION LAYER                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐   │
│  │   Web SPA     │  │   Desktop     │  │   CLI Tool    │  │   External API  │   │
│  │   (React)     │  │   (Electron)  │  │   (Go CLI)    │  │   (REST/gRPC)   │   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └────────┬────────┘   │
└──────────┼──────────────────┼──────────────────┼───────────────────┼────────────┘
           └──────────────────┴──────────────────┴───────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                     GATEWAY LAYER                                │ 
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                              API Gateway (Gin)                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ REST :8080  │  │ gRPC :9090  │  │ WS :8080/ws │  │ Auth/RateLimit  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
           ┌──────────────────────────────┴──────────────────────────────┐
           ▼                                                             ▼
┌─────────────────────────────────────┐       ┌─────────────────────────────────────┐
│         GO BACKEND (Core)           │       │      PYTHON QUANT (Math/ML)         │
│  ┌─────────────────────────────┐    │  gRPC │  ┌─────────────────────────────┐    │
│  │   Service Layer             │    │ ◄───► │  │   QSpectrum (Burg's MEM)    │    │
│  │   - MarketDataSvc           │    │       │  │   Phenomenological (DTW)    │    │
│  │   - AnnualCycleSvc          │    │       │  │   Walk-Forward Analysis     │    │
│  │   - CompositeSvc            │    │       │  │   Bootstrap CI              │    │
│  │   - COT/GBTC Analyzer       │    │       │  └─────────────────────────────┘    │
│  │   - Risk Management         │    │                                            │
│  │   - Backtest Engine         │    │       ┌─────────────────────────────┐    │
│  │   - Data Lineage            │    │       │   Libraries:                  │    │
│  └─────────────────────────────┘    │       │   - NumPy, SciPy              │    │
│                                      │       │   - Statsmodels               │    │
│  ┌─────────────────────────────┐    │       │   - scikit-learn              │    │
│  │   Repository Layer          │    │       └─────────────────────────────┘    │
│  │   - PostgreSQL              │    │                                            │
│  │   - TimescaleDB             │    │                                            │
│  │   - Redis                   │    │                                            │
│  └─────────────────────────────┘    │                                            │
└─────────────────────────────────────┘                                            │
           │                                                                       │
           ▼                                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                     DATA LAYER                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐   │
│  │ PostgreSQL 16 │  │ TimescaleDB   │  │ Redis 7       │  │ HashiCorp Vault │   │
│  │ (Primary DB)  │  │ (Time Series) │  │ (Cache/Queue) │  │ (Secrets)       │   │
│  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. СХЕМА БАЗЫ ДАННЫХ

### 2.1 Таблица `instruments`
```sql
CREATE TABLE instruments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol              VARCHAR(20) NOT NULL UNIQUE,
    name                VARCHAR(200),
    exchange            VARCHAR(50),
    type                VARCHAR(20) NOT NULL,
    currency            VARCHAR(10) DEFAULT 'USD',
    tick_size           DECIMAL(20, 10),
    is_active           BOOLEAN DEFAULT true,
    
    -- Crypto/GBTC адаптация
    proxy_type          VARCHAR(20),
    regime_change_date  DATE,
    day_close_utc       TIME,
    signal_direction    SMALLINT DEFAULT 1,
    proxy_list          JSONB,
    proxy_weights       JSONB,
    fte_threshold       NUMERIC DEFAULT 0.05,
    min_signal_distance INT DEFAULT 21,
    
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.2 Таблица `market_data` (TimescaleDB)
```sql
CREATE TABLE market_data (
    time                TIMESTAMP WITH TIME ZONE NOT NULL,
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    timeframe           VARCHAR(10) NOT NULL,
    open                DECIMAL(20, 8) NOT NULL,
    high                DECIMAL(20, 8) NOT NULL,
    low                 DECIMAL(20, 8) NOT NULL,
    close               DECIMAL(20, 8) NOT NULL,
    volume              BIGINT,
    adjusted_close      DECIMAL(20, 8),
    normalized_close    DECIMAL(10, 6),
    year_digit          SMALLINT,
    detrended_close     DECIMAL(20, 8),
    PRIMARY KEY (time, instrument_id, timeframe)
);

SELECT create_hypertable('market_data', 'time');

-- Continuous Aggregates
CREATE MATERIALIZED VIEW daily_annual_cycle
WITH (timescaledb.continuous) AS
SELECT 
    instrument_id,
    time_bucket('1 day', time) as bucket,
    avg(close) as avg_close
FROM market_data
GROUP BY instrument_id, bucket;

SELECT add_continuous_aggregate_policy('daily_annual_cycle',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### 2.3 Таблица `cot_data`
```sql
CREATE TABLE cot_data (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    report_date         DATE NOT NULL,
    
    -- Позиции (фьючерсы)
    commercials_long    BIGINT,
    commercials_short   BIGINT,
    commercials_net     BIGINT,
    large_specs_long    BIGINT,
    large_specs_short   BIGINT,
    small_specs_long    BIGINT,
    small_specs_short   BIGINT,
    
    -- Трасты/ETF (GBTC)
    premium             DECIMAL(10, 4),
    nav                 DECIMAL(20, 8),
    
    -- Индексы
    commercial_index    DECIMAL(5, 2),
    is_extreme          BOOLEAN,
    signal_type         VARCHAR(20),
    
    UNIQUE (instrument_id, report_date)
);
```

### 2.4 Таблица `backtest_results`
```sql
CREATE TABLE backtest_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name       VARCHAR(100) NOT NULL,
    instrument_id       UUID REFERENCES instruments(id),
    
    -- Период
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    is_in_sample        BOOLEAN,
    
    -- Метрики
    total_return        DECIMAL(10, 4),
    cagr                DECIMAL(10, 4),
    sharpe_ratio        DECIMAL(10, 4),
    max_drawdown        DECIMAL(10, 4),
    win_rate            DECIMAL(5, 4),
    profit_factor       DECIMAL(10, 4),
    total_trades        INTEGER,
    
    -- Статистика
    p_value             DECIMAL(5, 4),
    bootstrap_ci_lower  DECIMAL(10, 4),
    bootstrap_ci_upper  DECIMAL(10, 4),
    
    -- Equity curve (JSON)
    equity_curve        JSONB,
    
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.5 Таблица `signals`
```sql
CREATE TABLE signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id),
    signal_type         VARCHAR(10) NOT NULL,
    strength            DECIMAL(5, 4),
    initial_strength    DECIMAL(5, 4),
    half_life_days      INTEGER DEFAULT 14,
    age_days            INTEGER DEFAULT 0,
    reason              TEXT,
    target_time         TIMESTAMP WITH TIME ZONE,
    generated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status              VARCHAR(20) DEFAULT 'PENDING',
    triggered_at        TIMESTAMP WITH TIME ZONE,
    price_at_signal     DECIMAL(20, 8),
    
    -- Статистическая значимость
    p_value             DECIMAL(5, 4),
    confidence_level    DECIMAL(5, 4),
    
    -- Risk Management
    position_size       DECIMAL(20, 8),
    stop_loss           DECIMAL(20, 8),
    take_profit         DECIMAL(20, 8)
);
```

### 2.6 Таблица `data_lineage`
```sql
CREATE TABLE data_lineage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID NOT NULL REFERENCES signals(id),
    source_data     JSONB NOT NULL,
    transformations JSONB NOT NULL,
    parameters      JSONB,
    code_version    VARCHAR(40) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    checksum        VARCHAR(64) NOT NULL
);

CREATE INDEX idx_lineage_signal ON data_lineage(signal_id);
CREATE INDEX idx_lineage_timestamp ON data_lineage(timestamp);
```

---

## 3. МОДУЛИ И СЕРВИСЫ

### 3.1 Go Backend (Core)
| Модуль | Путь | Описание |
|--------|------|----------|
| MarketData | `internal/service/marketdata/` | Импорт, валидация, кэш, circuit breaker |
| AnnualCycle | `internal/service/seasonality/` | Сезонность, FTE адаптивный |
| Composite | `internal/service/cycle/` | Composite Line, U-Turn |
| COT/GBTC | `internal/service/cot/` | COT + GBTC адаптация |
| Risk | `internal/service/risk/` | Position Sizing, Signal Decay |
| Backtest | `internal/service/backtest/` | Симуляция, Bootstrap |
| Workflow | `internal/service/workflow/` | Интеграция всех модулей |
| Lineage | `internal/service/lineage/` | Data Lineage, Audit |

### 3.2 Python Quant (Math/ML)
| Модуль | Путь | Описание |
|--------|------|----------|
| QSpectrum | `quant/qspectrum/` | Циклическая корреляция, Burg's MEM |
| Phenomenological | `quant/phenom/` | DTW гибридный |
| WFA | `quant/wfa/` | Walk-Forward Analysis |
| Bootstrap | `quant/bootstrap/` | Доверительные интервалы (streaming) |

### 3.3 gRPC Proto
```protobuf
service QuantService {
    rpc QSpectrum(QSpectrumRequest) returns (QSpectrumResponse);
    rpc PhenomSearch(PhenomRequest) returns (PhenomResponse);
    rpc WalkForward(WFARequest) returns (WFAResponse);
    rpc Bootstrap(BootstrapRequest) returns (stream BootstrapProgress);
}

message BootstrapProgress {
    int32 current_iteration = 1;
    int32 total_iterations = 2;
    float progress_percent = 3;
    double ci_lower = 4;
    double ci_upper = 5;
}
```

---

## 4. API ENDPOINTS

```
# Market Data
POST   /api/v1/market/import
GET    /api/v1/market/symbols
GET    /api/v1/market/history
GET    /api/v1/market/history/aligned

# Analysis
POST   /api/v1/analysis/annual-cycle
POST   /api/v1/analysis/fte
POST   /api/v1/analysis/qspectrum
POST   /api/v1/analysis/composite
POST   /api/v1/analysis/decennial
POST   /api/v1/analysis/phenom
POST   /api/v1/analysis/uturn

# COT/GBTC
GET    /api/v1/cot/{symbol}
POST   /api/v1/cot/import

# Risk & Backtest
POST   /api/v1/risk/calculate
POST   /api/v1/backtest/run
GET    /api/v1/backtest/results/{id}

# Workflow
POST   /api/v1/workflow/williams
GET    /api/v1/signals/{symbol}

# Statistics
GET    /api/v1/stats/significance/{signal_id}
POST   /api/v1/stats/chow-test

# Lineage
GET    /api/v1/lineage/{signal_id}
```

---

## 5. КОНФИГУРАЦИЯ

```yaml
server:
  port: 8080
  grpc_port: 9090

database:
  postgres: "postgresql://user:pass@localhost:5432/cyclecast"
  redis: "redis://localhost:6379"

python_service:
  url: "python-quant:50051"
  timeout: 30s

backtest:
  require_before_production: true
  min_sharpe: 1.0
  max_drawdown: 0.20
  bootstrap_iterations: 1000

fte:
  base_threshold:
    crypto: 0.08
    tradfi: 0.05
  volatility_window: 30
  sensitivity_lambda: 0.5
  regime_detection: true

crypto:
  min_years: 10
  day_close_utc: "20:00:00"

gbtc:
  regime_change_date: "2024-01-11"
  signal_direction: -1
  proxy_list: ["GBTC", "IBIT"]
  min_signal_distance_days: 21

risk:
  per_trade_percent: 0.02
  max_drawdown: 0.20
  signal_half_life_days: 14

statistics:
  p_value_threshold: 0.05
  confidence_level: 0.95

market_data:
  providers:
    primary: yahoo
    fallback:
      - alphavantage
      - polygon
      - coingecko
  health_check_interval: 5m
  failover_strategy: round_robin

performance:
  dtw:
    max_window_years: 2
    use_fastdtw: true
    cache_redis: true
    cache_ttl: 24h
  
  burg_mem:
    max_order: 50
    incremental_update: true
    recalculate_threshold: 0.05

monitoring:
  prometheus: true
  grafana: true
  alerts:
    - FTE_degradation
    - GBTC_proxy_divergence
    - Signal_clustering
    - Python_service_latency
    - Circuit_breaker_open
    - Data_freshness
```

---

## 6. ФОРМУЛЫ И АЛГОРИТМЫ

### 6.1 FTE Адаптивный порог
```
threshold = base × (1 + λ × (current_vol / long_term_vol - 1))
где λ = 0.5 (sensitivity parameter)
```

### 6.2 GBTC Index (Percentile Rank)
```
Index_t = #{τ ∈ W : P_τ < P_t} / |W| × 100
```

### 6.3 Фильтр автокорреляции
```
После генерации сигнала в день t все сигналы того же типа 
в интервале [t+1, t + d] игнорируются, где d = min_signal_distance
```

### 6.4 Взвешенная агрегация прокси
```
Index_final,t = Σ(w_i × Index_i,t) / Σw_i
где w_i = Volume_i × AUM_i
```

### 6.5 Signal Decay
```
Effective_Strength = Initial_Strength × 0.5^(AgeDays / HalfLifeDays)
HalfLifeDays = 14 (по умолчанию)
```

### 6.6 DTW Гибридный
```
1. Грубая фильтрация: корреляция > 0.6 (O(N))
2. Ограничение топ-100 кандидатов
3. Параллельный exact DTW на кандидатах
4. Кэширование в Redis (TTL 24h)
```

---

## 7. МОНИТОРИНГ И ALERTING

```yaml
alerts:
  - name: FTE_degradation
    condition: fte_7d_avg < fte_30d_avg * 0.8
    severity: warning
    action: notify + recalibrate_model
  
  - name: GBTC_proxy_divergence
    condition: correlation(BTC, GBTC_premium) < 0.5 for 5 days
    severity: critical
    action: switch_to_onchain_proxy
  
  - name: Signal_clustering
    condition: signals_per_day > 3
    severity: warning
    action: activate_autocorrelation_filter
  
  - name: Python_service_latency
    condition: grpc_p99_latency > 1000ms
    severity: warning
    action: scale_python_workers
  
  - name: Circuit_breaker_open
    condition: circuit_state == OPEN for 5min
    severity: critical
    action: notify + fallback_to_cache
  
  - name: Data_freshness
    condition: last_update > 4h for market_data
    severity: critical
    action: alert + switch_to_backup_source
```

---

## 8. БЕЗОПАСНОСТЬ

### 8.1 Secrets Management
```
- API-ключи бирж → HashiCorp Vault
- DB credentials → Environment Variables (Docker Secrets)
- JWT keys → Rotated monthly
```

### 8.2 Audit Logging
```
- Все действия пользователей логируются
- Изменения конфигурации трекаются
- Доступ к API-ключам аудитится
- Data Lineage для каждого сигнала
```

---

## 9. DATA LINEAGE

### 9.1 Структура записи
```go
type DataLineage struct {
    ID              uuid.UUID         `json:"id"`
    SignalID        uuid.UUID         `json:"signal_id"`
    
    // Источники данных
    SourceData      []DataSource      `json:"source_data"`
    // - market_data_ids: []uuid
    // - cot_data_ids: []uuid
    // - data_hashes: map[string]string
    
    // Трансформации
    Transformations []Transform       `json:"transformations"`
    // - name: "annual_cycle", "qspectrum", etc.
    // - version: "v1.2.3"
    // - input_hash: string
    // - output_hash: string
    
    // Параметры модели
    Parameters      map[string]any    `json:"parameters"`
    
    // Метаданные
    CodeVersion     string            `json:"code_version"`  // git commit
    Timestamp       time.Time         `json:"timestamp"`
    Checksum        string            `json:"checksum"`      // SHA-256
}
```

### 9.2 API Endpoints
```
GET  /api/v1/lineage/{signal_id}           - Получить lineage по сигналу
GET  /api/v1/lineage/{signal_id}/export    - Экспорт для audit
POST /api/v1/lineage/verify                - Верификация целостности
```

---

## 10. CHAOS ENGINEERING

### 10.1 Сценарии тестирования
| ID | Сценарий | Ожидаемое поведение |
|----|----------|---------------------|
| CT-001 | Python service failure | Go использует кэш, возвращает partial results |
| CT-002 | Redis failure | Fallback to PostgreSQL, увеличенная latency |
| CT-003 | API load spike (10x) | Rate limiting активируется, graceful degradation |
| CT-004 | Database latency (>5s) | Circuit breaker открывается, timeout fallback |
| CT-005 | Network partition | gRPC retry с exponential backoff |

### 10.2 Инструменты
- **Chaos Mesh** для Kubernetes
- **Gremlin** для network faults
- **Custom scripts** для application-level faults

---

**Версия документации:** 3.2 Final  
**Статус:** ✅ УТВЕРЖДЕНО К РАЗРАБОТКЕ
