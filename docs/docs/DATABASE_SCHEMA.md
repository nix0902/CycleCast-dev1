# DATABASE SCHEMA

> **Версия:** 3.2 Final | **Database:** PostgreSQL 16 + TimescaleDB

---

## ER-ДИАГРАММА

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CORE ENTITIES                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   instruments    │
                    │──────────────────│
                    │ id (PK)          │
                    │ symbol           │
                    │ type             │
                    │ signal_direction │
                    │ regime_change_   │
                    │ date             │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┬───────────────────┐
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  market_data    │ │    cot_data     │ │ annual_cycles   │ │    signals      │
│─────────────────│ │─────────────────│ │─────────────────│ │─────────────────│
│ time (PK)       │ │ id (PK)         │ │ id (PK)         │ │ id (PK)         │
│ instrument_id   │ │ instrument_id   │ │ instrument_id   │ │ instrument_id   │
│ timeframe (PK)  │ │ report_date     │ │ year_digit      │ │ signal_type     │
│ open, high,     │ │ commercials_*   │ │ cycle_data      │ │ strength        │
│ low, close      │ │ premium, nav    │ │ confidence_data │ │ p_value         │
│ volume          │ │ commercial_     │ │ years_used      │ │ position_size   │
│ [TimescaleDB]   │ │ index           │ │ is_valid        │ │ stop_loss       │
└─────────────────┘ │ signal_type     │ │ fte_correlation │ │ take_profit     │
                    └─────────────────┘ └─────────────────┘ └────────┬────────┘
                                                                        │
                    ┌──────────────────┐                               │
                    │     cycles       │                               ▼
                    │──────────────────│                    ┌─────────────────┐
                    │ id (PK)          │                    │  data_lineage   │
                    │ instrument_id    │                    │─────────────────│
                    │ timeframe        │                    │ id (PK)         │
                    │ period           │                    │ signal_id (FK)  │
                    │ energy           │                    │ source_data     │
                    │ stability        │                    │ transformations │
                    │ correlation      │                    │ parameters      │
                    │ phase            │                    │ code_version    │
                    │ amplitude        │                    │ checksum        │
                    └────────┬─────────┘                    └─────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ composite_lines  │
                    │──────────────────│
                    │ id (PK)          │
                    │ instrument_id    │
                    │ short_cycle_id   │
                    │ medium_cycle_id  │
                    │ long_cycle_id    │
                    │ line_data        │
                    │ signals          │
                    │ uturns           │
                    └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   BACKTEST ENTITIES                                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│ backtest_results │
│──────────────────│
│ id (PK)          │
│ strategy_name    │
│ instrument_id    │
│ start_date       │
│ end_date         │
│ is_in_sample     │
│ total_return     │
│ sharpe_ratio     │
│ max_drawdown     │
│ win_rate         │
│ profit_factor    │
│ p_value          │
│ bootstrap_ci_*   │
│ equity_curve     │
└──────────────────┘
```

---

## 1. ТАБЛИЦА instruments

### Определение

```sql
CREATE TABLE instruments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol              VARCHAR(20) NOT NULL UNIQUE,
    name                VARCHAR(200),
    exchange            VARCHAR(50),
    type                VARCHAR(20) NOT NULL CHECK (type IN ('STOCK', 'INDEX', 'FOREX', 'COMMODITY', 'CRYPTO', 'FUTURES', 'ETF', 'TRUST')),
    currency            VARCHAR(10) DEFAULT 'USD',
    tick_size           DECIMAL(20, 10),
    is_active           BOOLEAN DEFAULT true,
    
    -- Crypto/GBTC адаптация
    proxy_type          VARCHAR(20) CHECK (proxy_type IN ('FUTURES', 'TRUST', 'ETF')),
    regime_change_date  DATE,
    day_close_utc       TIME,
    signal_direction    SMALLINT DEFAULT 1 CHECK (signal_direction IN (-1, 1)),
    proxy_list          JSONB,
    proxy_weights       JSONB,
    
    -- Валидация
    fte_threshold       NUMERIC(5, 4) DEFAULT 0.05,
    min_signal_distance INT DEFAULT 21,
    
    -- Метаданные
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_instruments_symbol ON instruments(symbol);
CREATE INDEX idx_instruments_type ON instruments(type);
CREATE INDEX idx_instruments_active ON instruments(is_active);
```

### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `symbol` | VARCHAR(20) | Тикер (BTC-USD, GBTC, SPY) |
| `type` | VARCHAR(20) | Тип инструмента |
| `proxy_type` | VARCHAR(20) | Для крипто: FUTURES, TRUST, ETF |
| `regime_change_date` | DATE | Дата структурного сдвига (GBTC: 2024-01-11) |
| `signal_direction` | SMALLINT | 1 = прямая, -1 = инверсия |
| `proxy_list` | JSONB | `["GBTC", "IBIT", "FBTC"]` |
| `proxy_weights` | JSONB | `{"GBTC": 0.5, "IBIT": 0.3}` |
| `fte_threshold` | NUMERIC | Порог FTE (Crypto: 0.08, TradFi: 0.05) |
| `min_signal_distance` | INT | Мин. дней между сигналами (21) |

### Пример записи

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "BTC-USD",
  "name": "Bitcoin USD",
  "type": "CRYPTO",
  "proxy_type": "TRUST",
  "signal_direction": -1,
  "proxy_list": ["GBTC", "IBIT", "FBTC"],
  "proxy_weights": {"GBTC": 0.5, "IBIT": 0.3, "FBTC": 0.2},
  "fte_threshold": 0.08,
  "min_signal_distance": 21
}
```

---

## 2. ТАБЛИЦА market_data (TimescaleDB)

### Определение

```sql
CREATE TABLE market_data (
    time                TIMESTAMP WITH TIME ZONE NOT NULL,
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    timeframe           VARCHAR(10) NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M')),
    open                DECIMAL(20, 8) NOT NULL,
    high                DECIMAL(20, 8) NOT NULL,
    low                 DECIMAL(20, 8) NOT NULL,
    close               DECIMAL(20, 8) NOT NULL,
    volume              BIGINT,
    adjusted_close      DECIMAL(20, 8),
    normalized_close    DECIMAL(10, 6),
    year_digit          SMALLINT CHECK (year_digit BETWEEN 0 AND 9),
    detrended_close     DECIMAL(20, 8),
    PRIMARY KEY (time, instrument_id, timeframe)
);

-- TimescaleDB Hypertable
SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);

-- Индексы
CREATE INDEX idx_market_data_instrument ON market_data(instrument_id, time DESC);
CREATE INDEX idx_market_data_timeframe ON market_data(timeframe);
CREATE INDEX idx_market_data_year_digit ON market_data(year_digit);

-- Continuous Aggregate для Annual Cycle
CREATE MATERIALIZED VIEW daily_stats
WITH (timescaledb.continuous) AS
SELECT 
    instrument_id,
    time_bucket('1 day', time) as day,
    AVG(close) as avg_close,
    STDDEV(close) as std_close,
    SUM(volume) as total_volume
FROM market_data
WHERE timeframe = '1d'
GROUP BY instrument_id, day;

SELECT add_continuous_aggregate_policy('daily_stats',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- Retention Policy (хранить тиковые данные 30 дней, дневные - вечно)
SELECT add_retention_policy('market_data', INTERVAL '30 days', if_not_exists => TRUE);
```

### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `time` | TIMESTAMP | Временная метка (UTC) |
| `instrument_id` | UUID | FK на instruments |
| `timeframe` | VARCHAR(10) | Таймфрейм |
| `open/high/low/close` | DECIMAL(20,8) | OHLC цены |
| `volume` | BIGINT | Объём |
| `adjusted_close` | DECIMAL(20,8) | Скорректированная цена |
| `normalized_close` | DECIMAL(10,6) | Нормализованная (0-1) |
| `year_digit` | SMALLINT | Год mod 10 (для Decennial) |
| `detrended_close` | DECIMAL(20,8) | Детрендированная цена |

---

## 3. ТАБЛИЦА cot_data

### Определение

```sql
CREATE TABLE cot_data (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
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
    price               DECIMAL(20, 8),
    volume              BIGINT,
    aum                 BIGINT,
    
    -- Индексы
    commercial_index    DECIMAL(5, 2),
    percentile_rank     DECIMAL(5, 2),
    is_extreme          BOOLEAN,
    signal_type         VARCHAR(20) CHECK (signal_type IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    
    -- Метаданные
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (instrument_id, report_date)
);

-- Индексы
CREATE INDEX idx_cot_instrument ON cot_data(instrument_id, report_date DESC);
CREATE INDEX idx_cot_extreme ON cot_data(is_extreme) WHERE is_extreme = TRUE;
CREATE INDEX idx_cot_signal ON cot_data(signal_type);
```

### Поля для GBTC

| Поле | Тип | Описание |
|------|-----|----------|
| `premium` | DECIMAL(10,4) | Премия/дисконт в % |
| `nav` | DECIMAL(20,8) | NAV на акцию |
| `percentile_rank` | DECIMAL(5,2) | Percentile Rank за 26 недель |
| `signal_type` | VARCHAR(20) | BULLISH (PR < 20), BEARISH (PR > 80) |

### Формула percentile_rank

```sql
-- Расчёт Percentile Rank
SELECT 
    report_date,
    premium,
    PERCENT_RANK() OVER (
        ORDER BY premium 
        ROWS BETWEEN 182 PRECEDING AND CURRENT ROW
    ) * 100 as percentile_rank
FROM cot_data
WHERE instrument_id = 'gbtc-uuid'
ORDER BY report_date;
```

---

## 4. ТАБЛИЦА signals

### Определение

```sql
CREATE TABLE signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    signal_type         VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL')),
    
    -- Сила сигнала
    strength            DECIMAL(5, 4) NOT NULL CHECK (strength BETWEEN 0 AND 1),
    initial_strength    DECIMAL(5, 4) NOT NULL,
    half_life_days      INTEGER DEFAULT 14,
    age_days            INTEGER DEFAULT 0,
    
    -- Причина и время
    reason              TEXT,
    target_time         TIMESTAMP WITH TIME ZONE,
    generated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status              VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'TRIGGERED', 'EXECUTED', 'EXPIRED', 'CANCELLED')),
    triggered_at        TIMESTAMP WITH TIME ZONE,
    executed_at         TIMESTAMP WITH TIME ZONE,
    price_at_signal     DECIMAL(20, 8),
    
    -- Статистическая значимость
    p_value             DECIMAL(5, 4),
    confidence_level    DECIMAL(5, 4) DEFAULT 0.95,
    bootstrap_ci_lower  DECIMAL(10, 4),
    bootstrap_ci_upper  DECIMAL(10, 4),
    
    -- Risk Management
    position_size       DECIMAL(20, 8),
    stop_loss           DECIMAL(20, 8),
    take_profit         DECIMAL(20, 8),
    risk_amount         DECIMAL(20, 8),
    
    -- Связи
    backtest_id         UUID REFERENCES backtest_results(id),
    
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_signals_instrument ON signals(instrument_id, generated_at DESC);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_signals_target_time ON signals(target_time) WHERE status = 'PENDING';
```

### Signal Decay

```sql
-- Обновление age_days и strength
UPDATE signals
SET 
    age_days = EXTRACT(DAY FROM NOW() - generated_at)::INTEGER,
    strength = initial_strength * POWER(0.5, EXTRACT(DAY FROM NOW() - generated_at)::FLOAT / half_life_days),
    updated_at = NOW()
WHERE status = 'PENDING';
```

---

## 5. ТАБЛИЦА cycles

### Определение

```sql
CREATE TABLE cycles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    timeframe           VARCHAR(10) NOT NULL,
    period              INTEGER NOT NULL CHECK (period >= 5),
    
    -- Характеристики цикла
    energy              DECIMAL(10, 6) NOT NULL,
    stability           DECIMAL(10, 6),
    correlation         DECIMAL(10, 6),
    phase               DECIMAL(10, 6),
    amplitude           DECIMAL(20, 8),
    
    -- МЭМ параметры
    mem_coefficients    DECIMAL[],
    
    -- Валидация
    wfa_score           DECIMAL(5, 4),
    is_dominant         BOOLEAN DEFAULT FALSE,
    
    -- Метаданные
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until         TIMESTAMP WITH TIME ZONE,
    
    UNIQUE (instrument_id, timeframe, period)
);

-- Индексы
CREATE INDEX idx_cycles_instrument ON cycles(instrument_id, timeframe);
CREATE INDEX idx_cycles_energy ON cycles(energy DESC);
CREATE INDEX idx_cycles_dominant ON cycles(is_dominant) WHERE is_dominant = TRUE;
```

---

## 6. ТАБЛИЦА composite_lines

### Определение

```sql
CREATE TABLE composite_lines (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    timeframe           VARCHAR(10) NOT NULL,
    
    -- Циклы
    short_cycle_id      UUID REFERENCES cycles(id),
    medium_cycle_id     UUID REFERENCES cycles(id),
    long_cycle_id       UUID REFERENCES cycles(id),
    
    -- Данные
    line_data           JSONB NOT NULL,
    projection_data     JSONB,
    signals             JSONB,
    uturns              JSONB,
    resonance_points    JSONB,
    
    -- Метаданные
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until         TIMESTAMP WITH TIME ZONE,
    
    UNIQUE (instrument_id, timeframe)
);
```

### Пример line_data

```json
{
  "points": [
    {"date": "2026-01-01", "value": 0.45, "direction": "up"},
    {"date": "2026-01-02", "value": 0.47, "direction": "up"}
  ],
  "cycles": [
    {"period": 14, "current_value": 0.8, "direction": "up"},
    {"period": 42, "current_value": 0.6, "direction": "up"},
    {"period": 98, "current_value": 0.4, "direction": "up"}
  ]
}
```

### Пример resonance_points

```json
[
  {"date": "2026-01-15", "type": "BUY", "strength": 0.85, "all_up": true},
  {"date": "2026-03-20", "type": "SELL", "strength": 0.72, "all_down": true}
]
```

---

## 7. ТАБЛИЦА annual_cycles

### Определение

```sql
CREATE TABLE annual_cycles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    year_digit          SMALLINT CHECK (year_digit BETWEEN 0 AND 9),
    
    -- Данные
    cycle_data          JSONB NOT NULL,
    confidence_data     JSONB,
    
    -- Статистика
    years_used          INTEGER NOT NULL,
    years_list          INTEGER[],
    is_valid            BOOLEAN DEFAULT TRUE,
    
    -- FTE
    fte_correlation     DECIMAL(5, 4),
    fte_threshold       DECIMAL(5, 4),
    fte_is_valid        BOOLEAN,
    
    -- Метаданные
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (instrument_id, year_digit)
);

-- Индексы
CREATE INDEX idx_annual_cycles_instrument ON annual_cycles(instrument_id);
CREATE INDEX idx_annual_cycles_year_digit ON annual_cycles(year_digit);
```

### Пример cycle_data

```json
{
  "days": [
    {"day": 1, "value": 0.45, "confidence": 0.72},
    {"day": 2, "value": 0.47, "confidence": 0.71}
  ],
  "monthly_avg": {
    "january": 0.52,
    "february": 0.48
  }
}
```

---

## 8. ТАБЛИЦА backtest_results

### Определение

```sql
CREATE TABLE backtest_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name       VARCHAR(100) NOT NULL,
    instrument_id       UUID REFERENCES instruments(id) ON DELETE SET NULL,
    
    -- Период
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    in_sample_end       DATE,
    is_in_sample        BOOLEAN DEFAULT FALSE,
    
    -- Параметры
    parameters          JSONB,
    initial_capital     DECIMAL(20, 2) DEFAULT 10000,
    commission          DECIMAL(5, 4) DEFAULT 0.001,
    slippage            DECIMAL(5, 4) DEFAULT 0.0005,
    
    -- Метрики
    total_return        DECIMAL(10, 4),
    cagr                DECIMAL(10, 4),
    sharpe_ratio        DECIMAL(10, 4),
    sortino_ratio       DECIMAL(10, 4),
    max_drawdown        DECIMAL(10, 4),
    max_drawdown_duration INTEGER,
    win_rate            DECIMAL(5, 4),
    profit_factor       DECIMAL(10, 4),
    expectancy          DECIMAL(20, 8),
    total_trades        INTEGER,
    winning_trades      INTEGER,
    losing_trades       INTEGER,
    avg_trade_duration  INTEGER,
    
    -- Статистика
    p_value             DECIMAL(5, 4),
    confidence_level    DECIMAL(5, 4) DEFAULT 0.95,
    bootstrap_ci_lower  DECIMAL(10, 4),
    bootstrap_ci_upper  DECIMAL(10, 4),
    bootstrap_iterations INTEGER DEFAULT 1000,
    
    -- Данные
    equity_curve        JSONB,
    trade_log           JSONB,
    daily_returns       JSONB,
    
    -- Статус
    status              VARCHAR(20) DEFAULT 'COMPLETED' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    error_message       TEXT,
    
    calculated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_name);
CREATE INDEX idx_backtest_instrument ON backtest_results(instrument_id);
CREATE INDEX idx_backtest_date ON backtest_results(calculated_at DESC);
```

---

## 9. ТАБЛИЦА data_lineage

### Определение

```sql
CREATE TABLE data_lineage (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id           UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    
    -- Источники данных
    source_data         JSONB NOT NULL,
    
    -- Трансформации
    transformations     JSONB NOT NULL,
    
    -- Параметры
    parameters          JSONB,
    
    -- Версионность
    code_version        VARCHAR(40) NOT NULL,
    config_version      VARCHAR(40),
    
    -- Целостность
    checksum            VARCHAR(64) NOT NULL,
    
    -- Метаданные
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_lineage_signal ON data_lineage(signal_id);
CREATE INDEX idx_lineage_code_version ON data_lineage(code_version);
CREATE INDEX idx_lineage_created ON data_lineage(created_at DESC);
```

### Пример source_data

```json
[
  {
    "type": "market_data",
    "id": "uuid",
    "symbol": "BTC-USD",
    "date_range": {"start": "2010-07-18", "end": "2026-01-01"},
    "hash": "sha256:abc123...",
    "row_count": 5844
  },
  {
    "type": "cot_data",
    "id": "uuid",
    "symbol": "GBTC",
    "date_range": {"start": "2024-01-11", "end": "2026-01-01"},
    "hash": "sha256:def456...",
    "row_count": 520
  }
]
```

### Пример transformations

```json
[
  {
    "name": "annual_cycle",
    "version": "v1.2.3",
    "input_hash": "sha256:abc123",
    "output_hash": "sha256:ghi789",
    "parameters": {"min_years": 10, "detrend_method": "ma"}
  },
  {
    "name": "qspectrum",
    "version": "v1.2.3",
    "input_hash": "sha256:ghi789",
    "output_hash": "sha256:jkl012",
    "parameters": {"min_period": 10, "max_period": 200}
  }
]
```

---

## 10. ТАБЛИЦА audit_log

### Определение

```sql
CREATE TABLE audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Кто
    user_id             UUID,
    user_email          VARCHAR(255),
    ip_address          INET,
    user_agent          TEXT,
    
    -- Что
    action              VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(50) NOT NULL,
    entity_id           UUID,
    
    -- Детали
    old_values          JSONB,
    new_values          JSONB,
    changes             JSONB,
    
    -- Результат
    status              VARCHAR(20) DEFAULT 'SUCCESS' CHECK (status IN ('SUCCESS', 'FAILURE')),
    error_message       TEXT,
    
    -- Время
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB
SELECT create_hypertable('audit_log', 'created_at', if_not_exists => TRUE);

-- Индексы
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- Retention (хранить 1 год)
SELECT add_retention_policy('audit_log', INTERVAL '1 year', if_not_exists => TRUE);
```

---

## 11. ТАБЛИЦА system_config

### Определение

```sql
CREATE TABLE system_config (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key                 VARCHAR(100) NOT NULL UNIQUE,
    value               JSONB NOT NULL,
    description         TEXT,
    is_encrypted        BOOLEAN DEFAULT FALSE,
    updated_by          UUID,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Примеры конфигурации
INSERT INTO system_config (key, value, description) VALUES
('fte.base_threshold.crypto', '0.08', 'Base FTE threshold for crypto'),
('fte.base_threshold.tradfi', '0.05', 'Base FTE threshold for TradFi'),
('gbtc.regime_change_date', '"2024-01-11"', 'GBTC ETF conversion date'),
('signal.half_life_days', '14', 'Default signal half-life'),
('risk.per_trade_percent', '0.02', 'Default risk per trade'),
('risk.max_drawdown', '0.20', 'Maximum drawdown limit');
```

---

## СВОДНАЯ ТАБЛИЦА

| Таблица | Тип | Назначение | TimescaleDB |
|---------|-----|------------|-------------|
| `instruments` | Reference | Инструменты | Нет |
| `market_data` | Time Series | OHLCV данные | ✅ Да |
| `cot_data` | Time Series | COT/GBTC данные | Нет |
| `signals` | Transaction | Торговые сигналы | Нет |
| `cycles` | Analysis | Циклы | Нет |
| `composite_lines` | Analysis | Composite Lines | Нет |
| `annual_cycles` | Analysis | Сезонность | Нет |
| `backtest_results` | Analysis | Результаты бэктестов | Нет |
| `data_lineage` | Audit | Data Lineage | Нет |
| `audit_log` | Audit | Аудит действий | ✅ Да |
| `system_config` | Reference | Конфигурация | Нет |

---

## ИНДЕКСЫ SUMMARY

```sql
-- Первичные ключи (автоматически)
-- Все таблицы имеют UUID PK

-- Внешние ключи
-- instrument_id -> instruments.id (CASCADE)
-- signal_id -> signals.id (CASCADE)
-- cycle_id -> cycles.id (SET NULL)

-- Производительные индексы
-- market_data: (instrument_id, time DESC), (timeframe), (year_digit)
-- signals: (instrument_id, generated_at DESC), (status), (target_time WHERE pending)
-- cot_data: (instrument_id, report_date DESC), (is_extreme), (signal_type)
-- cycles: (instrument_id, timeframe), (energy DESC), (is_dominant)
-- backtest_results: (strategy_name), (instrument_id), (calculated_at DESC)
-- data_lineage: (signal_id), (code_version), (created_at DESC)
-- audit_log: (user_id), (action), (entity_type, entity_id), (created_at DESC)
```

---

**Версия документации:** 3.2 Final
