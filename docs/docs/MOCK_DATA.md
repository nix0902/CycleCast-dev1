# MOCK DATA

> **Версия:** 3.2 Final | **CycleCast Test Data Specification**

---

## 1. ОБЗОР

Этот файл описывает схемы и примеры тестовых данных для разработки и тестирования CycleCast.

---

## 2. INSTRUMENTS (Инструменты)

### 2.1 Schema

```json
{
  "id": "uuid",
  "symbol": "string",
  "name": "string",
  "type": "STOCK|INDEX|FOREX|COMMODITY|CRYPTO|FUTURES|ETF|TRUST",
  "exchange": "string|null",
  "currency": "USD",
  "proxy_type": "FUTURES|TRUST|ETF|null",
  "signal_direction": 1|-1,
  "proxy_list": ["string"],
  "proxy_weights": {"symbol": 0.5},
  "fte_threshold": 0.05,
  "min_signal_distance": 21,
  "is_active": true
}
```

### 2.2 Seed Data

```sql
INSERT INTO instruments (id, symbol, name, type, currency, proxy_type, signal_direction, fte_threshold, min_signal_distance, proxy_list, proxy_weights) VALUES
-- Crypto
('a0000000-0000-0000-0000-000000000001', 'BTC-USD', 'Bitcoin USD', 'CRYPTO', 'USD', 'TRUST', -1, 0.08, 21, 
 '["GBTC", "IBIT", "FBTC"]'::jsonb, 
 '{"GBTC": 0.5, "IBIT": 0.3, "FBTC": 0.2}'::jsonb),
('a0000000-0000-0000-0000-000000000002', 'ETH-USD', 'Ethereum USD', 'CRYPTO', 'USD', 'TRUST', -1, 0.08, 21,
 '["ETHE"]'::jsonb, '{"ETHE": 1.0}'::jsonb),

-- TradFi with COT
('a0000000-0000-0000-0000-000000000003', 'SPY', 'S&P 500 ETF', 'ETF', 'USD', NULL, 1, 0.05, 21, NULL, NULL),
('a0000000-0000-0000-0000-000000000004', 'GC', 'Gold Futures', 'FUTURES', 'USD', 'FUTURES', 1, 0.05, 21, NULL, NULL),
('a0000000-0000-0000-0000-000000000005', 'CL', 'Crude Oil Futures', 'FUTURES', 'USD', 'FUTURES', 1, 0.05, 21, NULL, NULL),
('a0000000-0000-0000-0000-000000000006', 'ES', 'E-mini S&P 500', 'FUTURES', 'USD', 'FUTURES', 1, 0.05, 21, NULL, NULL),

-- GBTC Proxy
('a0000000-0000-0000-0000-000000000010', 'GBTC', 'Grayscale Bitcoin Trust', 'TRUST', 'USD', 'TRUST', -1, 0.08, 21, NULL, NULL),
('a0000000-0000-0000-0000-000000000011', 'IBIT', 'iShares Bitcoin ETF', 'ETF', 'USD', 'ETF', -1, 0.08, 21, NULL, NULL);
```

---

## 3. MARKET DATA (OHLCV)

### 3.1 Schema

```json
{
  "time": "2024-01-01T00:00:00Z",
  "instrument_id": "uuid",
  "timeframe": "1d",
  "open": 42000.00,
  "high": 43000.00,
  "low": 41500.00,
  "close": 42500.00,
  "volume": 25000000000,
  "adjusted_close": 42500.00
}
```

### 3.2 BTC-USD Sample (Daily, 2020-2025)

```csv
time,open,high,low,close,volume
2020-01-01,7200.00,7250.00,7150.00,7200.00,12345678900
2020-01-02,7200.00,7350.00,7180.00,7300.00,13456789000
...
2024-01-01,42000.00,43500.00,41500.00,42500.00,25000000000
```

### 3.3 Generator Function

```python
import numpy as np
from datetime import datetime, timedelta

def generate_btc_prices(start_date: str, end_date: str, seed: int = 42) -> list:
    """
    Generate realistic BTC price data with known cycles.
    
    Cycles embedded:
    - 14-day cycle (short)
    - 42-day cycle (medium)
    - 98-day cycle (long)
    - Annual seasonality
    """
    np.random.seed(seed)
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days
    
    t = np.arange(days)
    
    # Base trend (log-normal growth)
    trend = 7000 * np.exp(0.0008 * t)  # ~30% annual growth
    
    # Cycles
    short_cycle = 5000 * np.sin(2 * np.pi * t / 14)    # 14-day
    medium_cycle = 3000 * np.sin(2 * np.pi * t / 42)   # 42-day
    long_cycle = 2000 * np.sin(2 * np.pi * t / 98)     # 98-day
    
    # Annual seasonality (strong in Q4)
    annual = 3000 * np.sin(2 * np.pi * t / 365 - np.pi/4)
    
    # Noise
    noise = np.random.randn(days) * 1000
    
    # Combine
    close = trend + short_cycle + medium_cycle + long_cycle + annual + noise
    
    # Generate OHLCV
    data = []
    for i in range(days):
        date = start + timedelta(days=i)
        c = close[i]
        high = c * (1 + abs(np.random.randn()) * 0.02)
        low = c * (1 - abs(np.random.randn()) * 0.02)
        open_price = low + (high - low) * np.random.rand()
        volume = int(20e9 * (1 + 0.5 * np.random.randn()))
        
        data.append({
            "time": date.isoformat() + "Z",
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(c, 2),
            "volume": max(volume, 1e9)
        })
    
    return data
```

---

## 4. COT DATA

### 4.1 Futures Schema

```json
{
  "id": "uuid",
  "instrument_id": "uuid",
  "report_date": "2024-01-02",
  "commercials_long": 250000,
  "commercials_short": 450000,
  "commercials_net": -200000,
  "large_specs_long": 300000,
  "large_specs_short": 150000,
  "commercial_index": 25.5,
  "is_extreme": true,
  "signal_type": "BULLISH"
}
```

### 4.2 GBTC Schema

```json
{
  "id": "uuid",
  "instrument_id": "uuid",
  "report_date": "2024-01-15",
  "premium": -5.2,
  "nav": 45.00,
  "price": 42.66,
  "volume": 5000000,
  "percentile_rank": 15.2,
  "is_extreme": true,
  "signal_type": "BULLISH"
}
```

### 4.3 GBTC Sample Data (Post-Regime)

```sql
-- GBTC data after regime_change_date (2024-01-11)
INSERT INTO cot_data (id, instrument_id, report_date, premium, nav, price, percentile_rank, is_extreme, signal_type) VALUES
-- Extreme discount (bullish)
('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000010', '2024-01-15', -15.0, 45.00, 38.25, 5.0, true, 'BULLISH'),
('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000010', '2024-01-22', -12.0, 46.00, 40.48, 12.0, true, 'BULLISH'),
('b0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000010', '2024-01-29', -8.0, 47.00, 43.24, 22.0, false, 'NEUTRAL'),

-- Transition to premium (bearish)
('b0000000-0000-0000-0000-000000000010', 'a0000000-0000-0000-0000-000000000010', '2024-02-15', -2.0, 48.00, 47.04, 45.0, false, 'NEUTRAL'),
('b0000000-0000-0000-0000-000000000011', 'a0000000-0000-0000-0000-000000000010', '2024-02-22', 2.0, 50.00, 51.00, 65.0, false, 'NEUTRAL'),
('b0000000-0000-0000-0000-000000000012', 'a0000000-0000-0000-0000-000000000010', '2024-03-01', 8.0, 52.00, 56.16, 88.0, true, 'BEARISH');
```

---

## 5. SIGNALS

### 5.1 Schema

```json
{
  "id": "uuid",
  "instrument_id": "uuid",
  "signal_type": "BUY|SELL",
  "strength": 0.85,
  "initial_strength": 0.85,
  "age_days": 0,
  "half_life_days": 14,
  "reason": "Composite resonance + COT extreme + Phenom match",
  "target_time": "2024-01-15T00:00:00Z",
  "status": "PENDING|TRIGGERED|EXECUTED|EXPIRED",
  "price_at_signal": 42000.00,
  "p_value": 0.03,
  "position_size": 0.5,
  "stop_loss": 37800.00,
  "take_profit": 50400.00
}
```

### 5.2 Sample Signals

```sql
INSERT INTO signals (id, instrument_id, signal_type, strength, initial_strength, half_life_days, reason, target_time, status, price_at_signal, p_value, position_size, stop_loss, take_profit) VALUES
-- Strong BUY signal on BTC
('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'BUY', 0.85, 0.85, 14, 
 'Composite resonance (all 3 cycles up) + GBTC extreme discount (PR=5%) + Phenom match (2017 analog, corr=0.82)',
 '2024-01-15T00:00:00Z', 'TRIGGERED', 42000.00, 0.028, 0.5, 37800.00, 50400.00),

-- SELL signal
('c0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'SELL', 0.72, 0.72, 14,
 'Composite resonance (all 3 cycles down) + GBTC extreme premium (PR=88%)',
 '2024-03-15T00:00:00Z', 'PENDING', 58000.00, 0.042, 0.4, 63800.00, 46400.00);
```

---

## 6. BACKTEST RESULTS

### 6.1 Schema

```json
{
  "id": "uuid",
  "strategy_name": "williams_btc_v1",
  "instrument_id": "uuid",
  "start_date": "2015-01-01",
  "end_date": "2024-01-01",
  "in_sample_end": "2021-01-01",
  "total_return": 245.5,
  "cagr": 18.2,
  "sharpe_ratio": 1.35,
  "max_drawdown": 18.5,
  "win_rate": 0.52,
  "profit_factor": 1.85,
  "p_value": 0.03,
  "bootstrap_ci_lower": 85.2,
  "bootstrap_ci_upper": 420.5
}
```

### 6.2 Sample Result

```sql
INSERT INTO backtest_results (
    id, strategy_name, instrument_id, start_date, end_date, in_sample_end,
    total_return, cagr, sharpe_ratio, max_drawdown, win_rate, profit_factor,
    p_value, bootstrap_ci_lower, bootstrap_ci_upper, total_trades
) VALUES (
    'd0000000-0000-0000-0000-000000000001', 
    'williams_btc_v3', 
    'a0000000-0000-0000-0000-000000000001',
    '2015-01-01', '2024-01-01', '2021-01-01',
    245.5, 18.2, 1.35, 18.5, 0.52, 1.85,
    0.028, 85.2, 420.5, 156
);
```

---

## 7. ANNUAL CYCLES

### 7.1 Schema

```json
{
  "id": "uuid",
  "instrument_id": "uuid",
  "year_digit": null,
  "cycle_data": {
    "days": [{"day": 1, "value": 0.45, "confidence": 0.72}]
  },
  "years_used": 10,
  "fte_correlation": 0.12,
  "fte_threshold": 0.08,
  "fte_is_valid": true
}
```

### 7.2 Sample Annual Cycle

```json
{
  "cycle_data": {
    "days": [
      {"day": 1, "value": 0.42, "confidence": 0.68},
      {"day": 15, "value": 0.45, "confidence": 0.71},
      {"day": 30, "value": 0.48, "confidence": 0.72},
      {"day": 60, "value": 0.52, "confidence": 0.70},
      {"day": 90, "value": 0.58, "confidence": 0.74},
      {"day": 120, "value": 0.55, "confidence": 0.73},
      {"day": 150, "value": 0.50, "confidence": 0.71},
      {"day": 180, "value": 0.45, "confidence": 0.69},
      {"day": 210, "value": 0.48, "confidence": 0.70},
      {"day": 240, "value": 0.52, "confidence": 0.72},
      {"day": 270, "value": 0.55, "confidence": 0.74},
      {"day": 300, "value": 0.62, "confidence": 0.78},
      {"day": 330, "value": 0.68, "confidence": 0.82},
      {"day": 360, "value": 0.65, "confidence": 0.80}
    ],
    "monthly_avg": {
      "january": 0.45,
      "february": 0.48,
      "march": 0.52,
      "april": 0.58,
      "may": 0.55,
      "june": 0.50,
      "july": 0.45,
      "august": 0.48,
      "september": 0.52,
      "october": 0.60,
      "november": 0.68,
      "december": 0.65
    }
  },
  "years_used": 10,
  "fte_correlation": 0.12,
  "fte_is_valid": true
}
```

---

## 8. QSPECTRUM RESULT

### 8.1 Schema

```json
{
  "cycles": [
    {"period": 14, "energy": 0.85, "stability": 0.72, "correlation": 0.65}
  ],
  "top3": [
    {"period": 14, "energy": 0.85, "phase": 0.12, "amplitude": 0.08},
    {"period": 42, "energy": 0.72, "phase": 0.45, "amplitude": 0.06},
    {"period": 98, "energy": 0.61, "phase": 0.78, "amplitude": 0.04}
  ]
}
```

---

## 9. COMPOSITE LINE

### 9.1 Schema

```json
{
  "composite_line": [
    {"date": "2024-01-01", "value": 0.45, "direction": "up"}
  ],
  "resonance_points": [
    {"date": "2024-01-15", "type": "BUY", "strength": 0.85}
  ],
  "uturns": [
    {"date": "2024-01-15", "direction": "up", "confirmed": false}
  ]
}
```

---

## 10. DATA LINEAGE

### 10.1 Schema

```json
{
  "signal_id": "uuid",
  "source_data": [
    {
      "type": "market_data",
      "id": "uuid",
      "hash": "sha256:abc123...",
      "date_range": {"start": "2010-07-18", "end": "2024-01-01"},
      "row_count": 4900
    }
  ],
  "transformations": [
    {
      "name": "annual_cycle",
      "version": "v1.2.3",
      "input_hash": "sha256:input",
      "output_hash": "sha256:output",
      "parameters": {"min_years": 10}
    }
  ],
  "code_version": "abc123def456",
  "checksum": "sha256:final..."
}
```

---

## 11. SEED SCRIPT

### database/seeds/seed_all.sql

```sql
-- Run all seed files
\i seeds/instruments.sql
\i seeds/market_data_btc.sql
\i seeds/cot_gbtc.sql
\i seeds/signals.sql
\i seeds/backtest_results.sql

-- Update sequences
SELECT setval('instruments_id_seq', (SELECT MAX(id::text::int) FROM instruments));
```

---

## 12. GENERATOR COMMANDS

```bash
# Generate BTC test data
make generate-mock-data SYMBOL=BTC-USD YEARS=10

# Generate all seed files
make generate-seeds

# Load seeds to database
make seed-db
```

---

**Версия документации:** 3.2 Final
