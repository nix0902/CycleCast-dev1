# API Specification

> **Версия:** 3.2 Final | **CycleCast API v1**

---

## БАЗОВЫЙ URL

```
Development:  http://localhost:8080/api/v1
Production:   https://api.cyclecast.io/api/v1
gRPC:         localhost:9090
```

---

## АВТОРИЗАЦИЯ

### JWT Token
```http
Authorization: Bearer <token>
```

### API Key (для внешних систем)
```http
X-API-Key: <api_key>
```

---

## СОДЕРЖАНИЕ

1. [Market Data API](#1-market-data-api)
2. [Analysis API](#2-analysis-api)
3. [Seasonality Dashboard API](#3-seasonality-dashboard-api) ⭐ NEW
4. [COT/GBTC API](#4-cotgbtc-api)
5. [Backtest API](#5-backtest-api)
6. [Signals API](#6-signals-api)
7. [Risk Management API](#7-risk-management-api)
8. [Lineage API](#8-lineage-api)
9. [Workflow API](#9-workflow-api)
10. [gRPC Services](#10-grpc-services)
11. [WebSocket](#11-websocket)
12. [Error Codes](#12-error-codes)

---

## 3. SEASONALITY DASHBOARD API

> **Endpoint Base:** `/api/v1/seasonality`

API для Seasonality Dashboard React frontend. Предоставляет данные сезонного анализа, сигналы и метрики валидации FTE.

### 3.1 Получить анализ сезонности инструмента
```http
GET /api/v1/seasonality/{instrument_id}
```

**Параметры запроса:**

| Параметр | Тип | Обязательный | Описание | По умолчанию |
|----------|-----|--------------|----------|-------------|
| `instrument_id` | path string | Да | Идентификатор инструмента (SPX, GC, BTC) | - |
| `min_years` | query int | Нет | Минимальное количество лет данных | 30 |

**Ответ 200:**
```json
{
  "instrument_id": "SPX",
  "annual_cycle": {
    "instrument_id": "SPX",
    "years_analyzed": 45,
    "total_data_points": 11340,
    "seasonal_profile": [
      {
        "day_of_year": 1,
        "date": "2026-01-01",
        "avg_return": 0.0023,
        "std_dev": 0.0089,
        "win_rate": 0.62,
        "sample_size": 45,
        "percentile": 0.78
      }
    ],
    "peak_day": 185,
    "trough_day": 320,
    "amplitude": 0.045,
    "fte": {
      "pearson_correlation": 0.12,
      "spearman_correlation": 0.11,
      "direction_accuracy": 0.58,
      "volatility": 0.015,
      "adaptive_threshold": 0.085,
      "status": "VALID",
      "regime": "NORMAL_VOL",
      "last_validated": "2026-03-14T10:00:00Z"
    },
    "warnings": [],
    "last_data_point": "2026-03-13T21:00:00Z"
  },
  "seasonal_days": [...],
  "fte": {...},
  "last_updated": "2026-03-14T10:00:00Z",
  "data_quality": {
    "years_available": 45,
    "data_completeness": 0.98,
    "last_data_point": "2026-03-13T21:00:00Z",
    "warnings": []
  }
}
```

### 3.2 Получить текущий сигнал сезонности
```http
GET /api/v1/seasonality/{instrument_id}/signal
```

**Ответ 200:**
```json
{
  "id": "sig_sp500_20260314",
  "instrument_id": "SPX",
  "signal_type": "BUY",
  "strength": 0.72,
  "initial_strength": 0.72,
  "timestamp": "2026-03-14T10:00:00Z",
  "expiry_date": "2026-03-21T21:00:00Z",
  "metadata": {
    "source": "annual_cycle",
    "fte_validated": true,
    "regime": "NORMAL_VOL"
  }
}
```

### 3.3 Получить метрики FTE валидации
```http
GET /api/v1/seasonality/{instrument_id}/fte
```

**Ответ 200:**
```json
{
  "pearson_correlation": 0.12,
  "spearman_correlation": 0.11,
  "kendall_correlation": 0.09,
  "direction_accuracy": 0.58,
  "volatility": 0.015,
  "adaptive_threshold": 0.085,
  "status": "VALID",
  "regime": "NORMAL_VOL",
  "last_validated": "2026-03-14T10:00:00Z"
}
```

### 3.4 Запустить пересчёт сезонности (POST)
```http
POST /api/v1/seasonality/{instrument_id}/calculate?force=true
```

**Параметры:**
- `force` (query, bool): Принудительный пересчёт, игнорируя кэш (по умолчанию: false)

**Ответ 202:**
```json
{
  "instrument_id": "SPX",
  "status": "forced_recalculation",
  "years_analyzed": 45,
  "fte_valid": true,
  "timestamp": "2026-03-14T10:00:00Z"
}
```

### 3.5 WebSocket: Real-time обновления сигналов ⭐ NEW
```http
WS /api/v1/seasonality/{instrument_id}/stream
```

**Описание:** Устанавливает WebSocket соединение для получения push-уведомлений об изменениях сигналов сезонности.

**Протокол сообщений:**
```json
// Сервер → Клиент: Подтверждение подключения
{"type": "connected", "instrument": "SPX", "timestamp": "2026-03-14T10:00:00Z"}

// Сервер → Клиент: Обновление сигнала (каждые 30 сек)
{
  "type": "signal_update",
  "instrument": "SPX",
  "signal": {
    "id": "sig_sp500_20260314",
    "signal_type": "BUY",
    "strength": 0.72,
    "timestamp": "2026-03-14T10:00:30Z"
  },
  "timestamp": "2026-03-14T10:00:30Z"
}

// Клиент → Сервер: Контрольные сообщения
{"type": "ping"}           // → {"type": "pong", "timestamp": ...}
{"type": "subscribe"}     // Подписка на обновления (по умолчанию уже подписан)
{"type": "unsubscribe"}   // Закрытие соединения с сервера
```

**Пример использования (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/seasonality/SPX/stream');

ws.onopen = () => {
  console.log('Connected to seasonality stream');
  ws.send(JSON.stringify({type: 'subscribe'}));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'signal_update') {
    updateDashboard(data.signal);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

**Статусы FTE:**
- `VALID`: FTE > порог, сигнал достоверен для торговли
- `INVALID`: FTE < порог, сигнал слабый, требуется осторожность  
- `BROKEN`: Сезонность нарушена (3+ последовательных промаха)
- `INSUFFICIENT_DATA`: Недостаточно данных для валидации (<30 лет)

**Режимы волатильности (Regime):**
- `LOW_VOL`: Низкая волатильность — стандартный порог сигнала  
- `NORMAL_VOL`: Нормальная волатильность — базовый режим  
- `HIGH_VOL`: Высокая волатильность — порог ×1.2 (строже)  
- `EXTREME_VOL`: Экстремальная волатильность — порог ×1.5 (очень строго)

---

## 1. MARKET DATA API

### 1.1 Импорт исторических данных

```http
POST /api/v1/market/import
Content-Type: multipart/form-data
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "source": "yahoo",
  "timeframe": "1d",
  "start_date": "2010-01-01",
  "end_date": "2026-01-01",
  "file": "<csv_file>"  // опционально
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "instrument_id": "uuid",
    "points_imported": 5844,
    "gaps_detected": 3,
    "gaps_filled": 3,
    "first_date": "2010-07-18",
    "last_date": "2026-01-01"
  }
}
```

---

### 1.2 Получить список инструментов

```http
GET /api/v1/market/symbols?type=CRYPTO&is_active=true
```

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `type` | string | STOCK, INDEX, FOREX, COMMODITY, CRYPTO, FUTURES |
| `is_active` | boolean | Только активные |
| `page` | int | Страница (default: 1) |
| `limit` | int | Лимит (default: 50, max: 500) |

**Response:**
```json
{
  "status": "success",
  "data": {
    "instruments": [
      {
        "id": "uuid",
        "symbol": "BTC-USD",
        "name": "Bitcoin USD",
        "type": "CRYPTO",
        "exchange": null,
        "currency": "USD",
        "is_active": true,
        "proxy_type": "TRUST",
        "signal_direction": -1,
        "fte_threshold": 0.08,
        "min_signal_distance": 21,
        "data_points": 5844,
        "first_date": "2010-07-18",
        "last_date": "2026-01-01"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 127,
      "pages": 3
    }
  }
}
```

---

### 1.3 Получить исторические данные

```http
GET /api/v1/market/history?symbol=BTC-USD&timeframe=1d&start=2020-01-01&end=2026-01-01
```

**Query Parameters:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `symbol` | string | ✅ | Тикер инструмента |
| `timeframe` | string | ✅ | 1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M |
| `start` | date | ❌ | Начальная дата |
| `end` | date | ❌ | Конечная дата |
| `adjusted` | boolean | ❌ | Скорректированные цены (default: true) |

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "timeframe": "1d",
    "points": [
      {
        "time": "2020-01-01T00:00:00Z",
        "open": 7200.0,
        "high": 7250.0,
        "low": 7150.0,
        "close": 7200.0,
        "volume": 12345678900,
        "adjusted_close": 7200.0
      }
    ],
    "metadata": {
      "count": 2191,
      "first_date": "2020-01-01",
      "last_date": "2026-01-01"
    }
  }
}
```

---

### 1.4 Синхронизированные данные (для корреляций)

```http
GET /api/v1/market/history/aligned?symbols=BTC-USD,GBTC&timeframe=1d&start=2020-01-01
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbols": ["BTC-USD", "GBTC"],
    "timeframe": "1d",
    "alignment": "day_close_utc",
    "points": [
      {
        "time": "2020-01-01T20:00:00Z",
        "BTC-USD": {"close": 7200.0, "volume": 12345678900},
        "GBTC": {"close": 8.50, "volume": 5000000}
      }
    ]
  }
}
```

---

### 1.5 Удалить данные инструмента

```http
DELETE /api/v1/market/symbols/{symbol}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "TEST-USD",
    "points_deleted": 1000
  }
}
```

---

## 2. ANALYSIS API

### 2.1 Annual Cycle (Сезонность)

```http
POST /api/v1/analysis/annual-cycle
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "start_year": 2010,
  "end_year": 2026,
  "detrend_method": "ma",
  "detrend_period": 252,
  "normalize": true,
  "calculate_confidence": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "cycle": [
      {"day": 1, "value": 0.45, "confidence": 0.72},
      {"day": 2, "value": 0.47, "confidence": 0.71}
    ],
    "statistics": {
      "years_used": 15,
      "total_days": 366,
      "avg_confidence": 0.68,
      "best_month": "October",
      "worst_month": "March"
    },
    "fte_validation": {
      "correlation": 0.12,
      "threshold": 0.08,
      "is_valid": true
    }
  }
}
```

---

### 2.2 FTE Валидация

```http
POST /api/v1/analysis/fte
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "model_type": "annual_cycle",
  "in_sample_ratio": 0.7,
  "adaptive_threshold": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "correlation": 0.12,
    "threshold": 0.08,
    "threshold_type": "adaptive",
    "volatility_ratio": 1.2,
    "is_valid": true,
    "status": "PASS",
    "in_sample_period": {
      "start": "2010-07-18",
      "end": "2020-03-15"
    },
    "out_sample_period": {
      "start": "2020-03-16",
      "end": "2026-01-01"
    }
  }
}
```

---

### 2.3 QSpectrum Analysis

```http
POST /api/v1/analysis/qspectrum
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "start_date": "2015-01-01",
  "end_date": "2026-01-01",
  "min_period": 10,
  "max_period": 200,
  "energy_threshold": 0.3,
  "use_mem": true,
  "mem_order": 50,
  "wfa_windows": 5
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "cycles": [
      {"period": 14, "energy": 0.85, "stability": 0.72, "correlation": 0.65},
      {"period": 28, "energy": 0.72, "stability": 0.68, "correlation": 0.58},
      {"period": 56, "energy": 0.61, "stability": 0.55, "correlation": 0.45}
    ],
    "top3_cycles": [
      {"period": 14, "energy": 0.85, "phase": 0.12, "amplitude": 0.08},
      {"period": 42, "energy": 0.78, "phase": 0.45, "amplitude": 0.06},
      {"period": 98, "energy": 0.65, "phase": 0.78, "amplitude": 0.04}
    ],
    "mem_spectrum": {
      "freqs": [0.01, 0.02, "..."],
      "power": [0.8, 0.6, "..."]
    }
  }
}
```

---

### 2.4 Composite Line

```http
POST /api/v1/analysis/composite
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "cycles": [
    {"period": 14, "amplitude": 0.08, "phase": 0.12},
    {"period": 42, "amplitude": 0.06, "phase": 0.45},
    {"period": 98, "amplitude": 0.04, "phase": 0.78}
  ],
  "projection_days": 90,
  "detect_resonance": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "composite_line": [
      {"date": "2026-01-01", "value": 0.45, "direction": "up"},
      {"date": "2026-01-02", "value": 0.47, "direction": "up"}
    ],
    "projection": [
      {"date": "2026-01-02", "value": 0.52, "confidence": 0.68}
    ],
    "resonance_points": [
      {"date": "2026-01-15", "type": "BUY", "strength": 0.85},
      {"date": "2026-03-20", "type": "SELL", "strength": 0.72}
    ],
    "uturns": [
      {"date": "2026-01-15", "direction": "up", "confirmed": false}
    ]
  }
}
```

---

### 2.5 Decennial Patterns

```http
POST /api/v1/analysis/decennial
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "SPY",
  "current_year": 2026,
  "start_year": 1900
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "SPY",
    "current_year_digit": 6,
    "pattern": [
      {"day": 1, "value": 0.42},
      {"day": 2, "value": 0.45}
    ],
    "historical_years": [1906, 1916, 1926, "...", 2016],
    "years_count": 12,
    "correlation_with_current": 0.65,
    "is_enabled": true
  }
}
```

---

### 2.6 Phenomenological Model

```http
POST /api/v1/analysis/phenom
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "training_interval": 60,
  "use_decennial_filter": true,
  "current_year_digit": 6,
  "top_matches": 5,
  "projection_days": 30
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "best_matches": [
      {
        "start_date": "2017-11-01",
        "end_date": "2018-01-15",
        "dtw_distance": 0.15,
        "correlation": 0.85,
        "year": 2017,
        "year_digit": 7
      }
    ],
    "projection": [
      {"date": "2026-01-02", "value": 42000, "confidence": 0.72}
    ],
    "avg_correlation": 0.78,
    "method": "hybrid_dtw"
  }
}
```

---

### 2.7 U-Turn Detection

```http
POST /api/v1/analysis/uturn
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "lookback_days": 252,
  "threshold": 0.1
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "uturns": [
      {
        "date": "2026-01-15",
        "type": "BOTTOM",
        "price": 38000,
        "strength": 0.85,
        "confirmed": true
      }
    ]
  }
}
```

---

## 3. COT/GBTC API

### 3.1 Получить COT данные

```http
GET /api/v1/cot/{symbol}?start=2020-01-01&end=2026-01-01
```

**Response (Futures):**
```json
{
  "status": "success",
  "data": {
    "symbol": "GC",
    "type": "FUTURES",
    "reports": [
      {
        "report_date": "2026-01-01",
        "commercials_long": 250000,
        "commercials_short": 450000,
        "commercials_net": -200000,
        "commercial_index": 25.5,
        "is_extreme": true,
        "signal_type": "BULLISH"
      }
    ]
  }
}
```

**Response (GBTC/ETF):**
```json
{
  "status": "success",
  "data": {
    "symbol": "GBTC",
    "type": "TRUST",
    "reports": [
      {
        "report_date": "2026-01-01",
        "premium": -5.2,
        "nav": 45.0,
        "price": 42.66,
        "percentile_rank": 15.2,
        "is_extreme": true,
        "signal_type": "BULLISH",
        "signal_direction": -1
      }
    ],
    "regime_change_date": "2024-01-11",
    "post_regime_only": true
  }
}
```

---

### 3.2 Импорт COT данных

```http
POST /api/v1/cot/import
Content-Type: application/json
```

**Request:**
```json
{
  "type": "FUTURES",
  "source": "cftc",
  "symbols": ["GC", "SI", "CL"]
}
```

---

### 3.3 Рассчитать GBTC Index

```http
POST /api/v1/cot/gbtc
Content-Type: application/json
```

**Request:**
```json
{
  "symbol": "BTC-USD",
  "proxy_list": ["GBTC", "IBIT", "FBTC"],
  "window_weeks": 26,
  "regime_change_date": "2024-01-11",
  "min_signal_distance": 21,
  "aggregation": "liquidity_weighted"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTC-USD",
    "index": 18.5,
    "proxy_data": {
      "GBTC": {"premium": -5.2, "weight": 0.5, "index": 15.2},
      "IBIT": {"premium": 0.1, "weight": 0.3, "index": 52.0},
      "FBTC": {"premium": -0.2, "weight": 0.2, "index": 35.0}
    },
    "signal": {
      "type": "BULLISH",
      "direction": -1,
      "strength": 0.82,
      "last_signal_date": "2026-01-01",
      "next_valid_date": "2026-01-22"
    }
  }
}
```

---

## 4. BACKTEST API

### 4.1 Запуск бэктеста

```http
POST /api/v1/backtest/run
Content-Type: application/json
```

**Request:**
```json
{
  "strategy_name": "williams_btc_v1",
  "symbol": "BTC-USD",
  "timeframe": "1d",
  "start_date": "2015-01-01",
  "end_date": "2026-01-01",
  "in_sample_ratio": 0.7,
  "initial_capital": 10000,
  "commission": 0.001,
  "slippage": 0.0005,
  "bootstrap_iterations": 1000,
  "confidence_level": 0.95,
  "parameters": {
    "annual_cycle_min_years": 10,
    "fte_threshold": 0.08,
    "position_risk_percent": 0.02,
    "max_drawdown": 0.20,
    "signal_half_life": 14
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "backtest_id": "uuid",
    "strategy_name": "williams_btc_v1",
    "symbol": "BTC-USD",
    "period": {
      "start": "2015-01-01",
      "end": "2026-01-01",
      "in_sample_end": "2022-04-01"
    },
    "metrics": {
      "total_return": 245.5,
      "cagr": 18.2,
      "sharpe_ratio": 1.35,
      "max_drawdown": 18.5,
      "win_rate": 0.52,
      "profit_factor": 1.85,
      "total_trades": 156
    },
    "statistics": {
      "p_value": 0.03,
      "bootstrap_ci_lower": 85.2,
      "bootstrap_ci_upper": 420.5,
      "is_significant": true
    },
    "equity_curve": [
      {"date": "2015-01-01", "equity": 10000},
      {"date": "2015-01-02", "equity": 10100}
    ]
  }
}
```

---

### 4.2 Получить результаты бэктеста

```http
GET /api/v1/backtest/results/{backtest_id}
```

---

### 4.3 Список бэктестов

```http
GET /api/v1/backtest/results?symbol=BTC-USD&limit=10
```

---

## 5. SIGNALS API

### 5.1 Получить сигналы

```http
GET /api/v1/signals?symbol=BTC-USD&status=PENDING&limit=50
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "signals": [
      {
        "id": "uuid",
        "instrument_id": "uuid",
        "symbol": "BTC-USD",
        "signal_type": "BUY",
        "strength": 0.85,
        "initial_strength": 0.85,
        "age_days": 0,
        "half_life_days": 14,
        "reason": "Composite resonance + COT extreme + Phenom match",
        "target_time": "2026-01-15T00:00:00Z",
        "generated_at": "2026-01-01T10:00:00Z",
        "status": "PENDING",
        "price_at_signal": 42000,
        "p_value": 0.03,
        "confidence_level": 0.95,
        "position_size": 0.5,
        "stop_loss": 37800,
        "take_profit": 50400
      }
    ]
  }
}
```

---

### 5.2 Обновить статус сигнала

```http
PATCH /api/v1/signals/{signal_id}
Content-Type: application/json
```

**Request:**
```json
{
  "status": "EXECUTED",
  "triggered_at": "2026-01-15T10:30:00Z",
  "execution_price": 42100
}
```

---

## 6. RISK MANAGEMENT API

### 6.1 Расчёт позиции

```http
POST /api/v1/risk/calculate
Content-Type: application/json
```

**Request:**
```json
{
  "signal_id": "uuid",
  "account_balance": 100000,
  "current_drawdown": 0.05,
  "risk_config": {
    "per_trade_percent": 0.02,
    "max_drawdown": 0.20,
    "signal_half_life": 14
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "position": {
      "size": 1.2,
      "entry": 42000,
      "stop_loss": 37800,
      "take_profit": 50400,
      "risk_amount": 2000,
      "effective_strength": 0.85,
      "is_rejected": false
    },
    "risk_metrics": {
      "risk_per_trade": "2%",
      "potential_loss": "$5040",
      "potential_gain": "$10080",
      "risk_reward_ratio": 2.0
    }
  }
}
```

---

## 7. LINEAGE API

### 7.1 Получить Data Lineage

```http
GET /api/v1/lineage/{signal_id}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "signal_id": "uuid",
    "source_data": [
      {
        "type": "market_data",
        "id": "uuid",
        "symbol": "BTC-USD",
        "hash": "sha256:abc123...",
        "date_range": "2010-07-18 to 2026-01-01"
      },
      {
        "type": "cot_data",
        "id": "uuid",
        "symbol": "GBTC",
        "hash": "sha256:def456...",
        "date_range": "2024-01-11 to 2026-01-01"
      }
    ],
    "transformations": [
      {
        "name": "annual_cycle",
        "version": "v1.2.3",
        "input_hash": "sha256:abc123",
        "output_hash": "sha256:ghi789",
        "parameters": {"min_years": 10}
      },
      {
        "name": "qspectrum",
        "version": "v1.2.3",
        "input_hash": "sha256:ghi789",
        "output_hash": "sha256:jkl012"
      }
    ],
    "code_version": "abc123def456",
    "timestamp": "2026-01-01T10:00:00Z",
    "checksum": "sha256:mno345..."
  }
}
```

---

### 7.2 Экспорт для аудита

```http
GET /api/v1/lineage/{signal_id}/export?format=json
```

---

### 7.3 Верификация целостности

```http
POST /api/v1/lineage/verify
Content-Type: application/json
```

**Request:**
```json
{
  "signal_id": "uuid"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "is_valid": true,
    "verified_at": "2026-01-01T10:00:00Z",
    "checksums_match": true
  }
}
```

---

## 8. WORKFLOW API

### 8.1 Запуск полного Williams Workflow

```http
POST /api/v1/workflow/williams
Content-Type: application/json
```

**Request:**
```json
{
  "symbols": ["BTC-USD", "ETH-USD", "SPY"],
  "require_backtest": true,
  "paper_trading": false,
  "parameters": {
    "annual_cycle_min_years": 10,
    "fte_threshold_crypto": 0.08,
    "fte_threshold_tradfi": 0.05,
    "position_risk_percent": 0.02,
    "max_drawdown": 0.20
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workflow_id": "uuid",
    "status": "COMPLETED",
    "results": {
      "BTC-USD": {
        "annual_cycle_valid": true,
        "composite_signal": "BUY",
        "cot_signal": "BULLISH",
        "phenom_correlation": 0.78,
        "final_signal": "BUY",
        "signal_strength": 0.82
      }
    },
    "signals_generated": 2,
    "execution_time_ms": 1250
  }
}
```

---

## 9. gRPC SERVICES

### Proto Definition (quant/proto/quant.proto)

```protobuf
syntax = "proto3";

package quant;

// ========== QSpectrum ==========

message QSpectrumRequest {
  repeated double prices = 1;
  int32 min_period = 2;
  int32 max_period = 3;
  double energy_threshold = 4;
  bool use_mem = 5;
  int32 mem_order = 6;
  int32 wfa_windows = 7;
}

message Cycle {
  int32 period = 1;
  double energy = 2;
  double stability = 3;
  double correlation = 4;
  double phase = 5;
  double amplitude = 6;
}

message QSpectrumResponse {
  repeated Cycle cycles = 1;
  repeated Cycle top3 = 2;
  repeated double mem_freqs = 3;
  repeated double mem_power = 4;
}

// ========== Phenom ==========

message PhenomRequest {
  repeated double prices = 1;
  int32 training_interval = 2;
  bool use_decennial_filter = 3;
  int32 current_year_digit = 4;
  int32 top_matches = 5;
  double correlation_threshold = 6;
}

message PatternMatch {
  int32 start_index = 1;
  int32 end_index = 2;
  double dtw_distance = 3;
  double correlation = 4;
  int32 year = 5;
  int32 year_digit = 6;
}

message PhenomResponse {
  repeated PatternMatch best_matches = 1;
  repeated double projection = 2;
  double avg_correlation = 3;
}

// ========== Bootstrap ==========

message BootstrapRequest {
  repeated double returns = 1;
  int32 iterations = 2;
  double confidence_level = 3;
}

message BootstrapProgress {
  int32 current_iteration = 1;
  int32 total_iterations = 2;
  float progress_percent = 3;
  double ci_lower = 4;
  double ci_upper = 5;
  double current_mean = 6;
}

message BootstrapResponse {
  double ci_lower = 1;
  double ci_upper = 2;
  double p_value = 3;
  double mean = 4;
  double std = 5;
}

// ========== Chow Test ==========

message ChowTestRequest {
  repeated double data = 1;
  int32 breakpoint_index = 2;
}

message ChowTestResponse {
  double f_statistic = 1;
  double p_value = 2;
  bool is_structural_break = 3;
}

// ========== Service ==========

service QuantService {
  rpc QSpectrum(QSpectrumRequest) returns (QSpectrumResponse);
  rpc PhenomSearch(PhenomRequest) returns (PhenomResponse);
  rpc Bootstrap(BootstrapRequest) returns (stream BootstrapProgress);
  rpc ChowTest(ChowTestRequest) returns (ChowTestResponse);
}
```

---

## 10. WEBSOCKET

### 10.1 Подключение

```javascript
ws://localhost:8080/ws
```

### 10.2 Подписка на сигналы

```json
{
  "action": "subscribe",
  "channel": "signals",
  "symbols": ["BTC-USD", "ETH-USD"]
}
```

### 10.3 Получение сигнала

```json
{
  "channel": "signals",
  "data": {
    "symbol": "BTC-USD",
    "signal_type": "BUY",
    "strength": 0.85,
    "price": 42000,
    "timestamp": "2026-01-01T10:00:00Z"
  }
}
```

### 10.4 Подписка на прогресс бэктеста

```json
{
  "action": "subscribe",
  "channel": "backtest",
  "backtest_id": "uuid"
}
```

```json
{
  "channel": "backtest",
  "data": {
    "backtest_id": "uuid",
    "progress_percent": 45,
    "current_iteration": 450,
    "total_iterations": 1000
  }
}
```

---

## 11. ERROR CODES

### HTTP Status Codes

| Code | Описание |
|------|----------|
| 200 | Успех |
| 201 | Создано |
| 400 | Неверный запрос |
| 401 | Не авторизован |
| 403 | Доступ запрещён |
| 404 | Не найдено |
| 422 | Ошибка валидации |
| 429 | Rate limit превышен |
| 500 | Внутренняя ошибка |
| 503 | Сервис недоступен |

### Application Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `MD001` | Insufficient data | Недостаточно исторических данных |
| `MD002` | Invalid timeframe | Неверный таймфрейм |
| `MD003` | Data gap detected | Обнаружен пропуск данных |
| `AC001` | Min years not met | Минимум лет не достигнут |
| `AC002` | FTE validation failed | FTE валидация не пройдена |
| `QS001` | No dominant cycles | Доминантные циклы не найдены |
| `COT001` | COT data not available | COT данные недоступны |
| `COT002` | Invalid proxy configuration | Неверная конфигурация прокси |
| `BT001` | Backtest failed | Бэктест завершился с ошибкой |
| `BT002` | Negative equity | Отрицательный equity |
| `RM001` | Max drawdown exceeded | Превышен макс. drawdown |
| `RM002` | Invalid stop loss | Неверный stop-loss |
| `LN001` | Lineage verification failed | Верификация lineage не пройдена |

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "AC001",
    "message": "Minimum years requirement not met",
    "details": {
      "required_years": 10,
      "actual_years": 5
    }
  }
}
```

---

## RATE LIMITING

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Market Data | 100 | 1 minute |
| Analysis | 30 | 1 minute |
| Backtest | 5 | 1 minute |
| Signals | 60 | 1 minute |
| WebSocket | 10 connections | - |

---

**Версия документации:** 3.2 Final
