# CONVENTIONS

> **Версия:** 3.2 Final | **CycleCast Project**

---

## 1. ОБЩИЕ ПРИНЦИПЫ

### 1.1 Языки
- **Код:** Английский
- **Комментарии:** Английский
- **Документация:** Русский (основной), English (optional)
- **API:** Английский

### 1.2 Форматирование
- **Отступы:** 4 пробела (Go), 2 пробела (TypeScript/Python)
- **Длина строки:** max 120 символов
- **Кодировка:** UTF-8
- **Конец строки:** LF (Unix-style)

---

## 2. GO BACKEND

### 2.1 Naming Conventions

#### Пакеты
```go
// lowercase, одно слово
package marketdata
package seasonality
package cot
```

#### Файлы
```go
// snake_case
marketdata_service.go
marketdata_service_test.go
marketdata_repository.go
```

#### Типы (PascalCase)
```go
// Interfaces: существительное + "er" или просто существительное
type MarketDataReader interface {}
type Analyzer interface {}

// Structs: существительное
type MarketData struct {}
type AnnualCycle struct {}

// Конструкторы: New + TypeName
func NewMarketDataService(repo MarketDataRepository) *MarketDataService
```

#### Функции/Методы (PascalCase если exported, camelCase если private)
```go
// Exported
func (s *Service) GetMarketData(symbol string) (*MarketData, error)

// Private
func (s *Service) validateData(data *MarketData) error
```

#### Константы
```go
// PascalCase для exported
const (
    DefaultMinYears    = 10
    DefaultFTEThreshold = 0.08
)

// camelCase для private
const (
    defaultTimeout = 30 * time.Second
)
```

#### Ошибки
```go
// Ошибки начинаются с "Err"
var (
    ErrInsufficientData = errors.New("insufficient data")
    ErrInvalidSymbol    = errors.New("invalid symbol")
)

// Ошибки с контекстом
type ValidationError struct {
    Field   string
    Value   interface{}
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation error on field %s: %s", e.Field, e.Message)
}
```

### 2.2 Структура модуля

```
service/marketdata/
├── service.go           // Interface definition
├── service_impl.go      // Implementation
├── repository.go        // Repository interface
├── repository_pg.go     // PostgreSQL implementation
├── models.go            // Domain models
├── errors.go            // Errors
├── service_test.go      // Tests
└── repository_test.go
```

### 2.3 Interface Definitions

```go
// service.go
package marketdata

// Service provides market data operations.
type Service interface {
    // Get retrieves market data for a symbol.
    Get(ctx context.Context, symbol string, opts GetOptions) (*MarketData, error)
    
    // Import imports historical data from external source.
    Import(ctx context.Context, req ImportRequest) (*ImportResult, error)
    
    // Validate checks data quality.
    Validate(ctx context.Context, symbol string) (*ValidationResult, error)
}
```

### 2.4 Error Handling

```go
// Всегда проверяем ошибки
if err != nil {
    return nil, fmt.Errorf("failed to get market data: %w", err)
}

// Используем errors.Is и errors.As
if errors.Is(err, ErrInsufficientData) {
    // handle
}

var validationErr *ValidationError
if errors.As(err, &validationErr) {
    // handle
}
```

### 2.5 Context Usage

```go
// Всегда передаём context первым параметром
func (s *Service) Get(ctx context.Context, symbol string) (*MarketData, error)

// Используем context для timeout
ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
defer cancel()
```

### 2.6 Logging

```go
// Структурированное логирование (slog)
import "log/slog"

// Уровни: Debug, Info, Warn, Error
slog.Info("importing market data",
    "symbol", symbol,
    "points", len(data),
)

slog.Error("failed to import",
    "symbol", symbol,
    "error", err,
)
```

### 2.7 Testing

```go
// Файл: service_test.go
package marketdata

import "testing"

func TestService_Get(t *testing.T) {
    tests := []struct {
        name    string
        symbol  string
        want    *MarketData
        wantErr error
    }{
        {
            name:   "valid symbol",
            symbol: "BTC-USD",
            want:   &MarketData{Symbol: "BTC-USD"},
        },
        {
            name:    "invalid symbol",
            symbol:  "INVALID",
            wantErr: ErrInvalidSymbol,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // test body
        })
    }
}
```

---

## 3. PYTHON QUANT

### 3.1 Naming Conventions

#### Модули/Пакеты
```python
# snake_case
qspectrum/
phenom/
bootstrap/
```

#### Классы (PascalCase)
```python
class QSpectrumAnalyzer:
    pass

class DTWMatcher:
    pass
```

#### Функции/Методы (snake_case)
```python
def calculate_spectrum(prices: np.ndarray) -> List[dict]:
    pass

def _normalize_data(self, data: np.ndarray) -> np.ndarray:
    pass  # private method
```

#### Переменные (snake_case)
```python
cycle_energy = 0.85
annual_cycle = AnnualCycle()
```

#### Константы (UPPER_SNAKE_CASE)
```python
DEFAULT_MIN_PERIOD = 10
DEFAULT_MAX_PERIOD = 200
BOOTSTRAP_ITERATIONS = 1000
```

### 3.2 Type Hints

```python
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from numpy.typing import NDArray

def calculate_dtw(
    target: NDArray[np.float64],
    history: NDArray[np.float64],
    config: Optional[Dict[str, Any]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate DTW distance between target and history.
    
    Args:
        target: Target time series
        history: Historical time series
        config: Optional configuration
    
    Returns:
        Tuple of (distance, metadata)
    """
    pass
```

### 3.3 Docstrings (Google Style)

```python
def calculate_qspectrum(
    prices: np.ndarray,
    min_period: int = 10,
    max_period: int = 200
) -> QSpectrumResult:
    """
    Calculate QSpectrum for price data.
    
    Args:
        prices: Array of historical prices
        min_period: Minimum cycle period to search
        max_period: Maximum cycle period to search
    
    Returns:
        QSpectrumResult containing:
            - cycles: List of detected cycles
            - top3: Top 3 dominant cycles
            - mem_spectrum: MEM spectral density
    
    Raises:
        ValueError: If prices array is empty or too short
        InsufficientDataError: If insufficient data for analysis
    
    Example:
        >>> prices = get_prices("BTC-USD")
        >>> result = calculate_qspectrum(prices)
        >>> print(result.top3[0].period)
        14
    """
    pass
```

### 3.4 Error Handling

```python
class CycleCastError(Exception):
    """Base exception for CycleCast."""
    pass

class InsufficientDataError(CycleCastError):
    """Raised when insufficient data for analysis."""
    def __init__(self, required: int, actual: int):
        self.required = required
        self.actual = actual
        super().__init__(
            f"Insufficient data: required {required}, got {actual}"
        )

# Usage
if len(prices) < MIN_PRICES:
    raise InsufficientDataError(MIN_PRICES, len(prices))
```

### 3.5 Configuration

```python
# config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class QSpectrumConfig:
    min_period: int = 10
    max_period: int = 200
    energy_threshold: float = 0.3
    use_mem: bool = True
    mem_order: int = 50
    wfa_windows: int = 5
    
    @classmethod
    def from_dict(cls, d: dict) -> "QSpectrumConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
```

---

## 4. TYPESCRIPT FRONTEND

### 4.1 Naming Conventions

#### Файлы
```
// Компоненты: PascalCase.tsx
CompositeLineChart.tsx
AnnualCyclePanel.tsx

// Утилиты: camelCase.ts
apiClient.ts
dateUtils.ts

// Типы: PascalCase.ts
MarketData.ts
Signal.ts

// Хуки: use*.ts
useAnnualCycle.ts
useSignals.ts
```

#### Компоненты (PascalCase)
```tsx
export function CompositeLineChart({ data, config }: CompositeLineChartProps) {
  return (
    <div className="composite-line-chart">
      {/* ... */}
    </div>
  );
}
```

#### Функции/Переменные (camelCase)
```typescript
const fetchMarketData = async (symbol: string) => {
  // ...
};

const annualCycleData = await fetchAnnualCycle("BTC-USD");
```

#### Интерфейсы/Типы (PascalCase)
```typescript
interface MarketData {
  symbol: string;
  timestamp: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

type SignalType = "BUY" | "SELL";
```

#### Константы (UPPER_SNAKE_CASE или camelCase для объектов)
```typescript
export const API_BASE_URL = "http://localhost:8080/api/v1";

export const DEFAULT_CONFIG = {
  minYears: 10,
  fteThreshold: 0.08,
};
```

### 4.2 Component Structure

```tsx
// imports
import { useState, useEffect } from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";

// types
interface AnnualCycleChartProps {
  symbol: string;
  data: AnnualCycleData;
  config?: ChartConfig;
}

// component
export function AnnualCycleChart({ 
  symbol, 
  data, 
  config = DEFAULT_CONFIG 
}: AnnualCycleChartProps) {
  // hooks
  const [isLoading, setIsLoading] = useState(false);
  
  // effects
  useEffect(() => {
    // ...
  }, [symbol]);
  
  // handlers
  const handleClick = () => {
    // ...
  };
  
  // render
  return (
    <Card>
      <CardHeader>{symbol}</CardHeader>
      <CardContent>
        {/* chart content */}
      </CardContent>
    </Card>
  );
}
```

### 4.3 API Client

```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;
  
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });
  }
  
  const response = await fetch(url.toString(), {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    },
  });
  
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  
  return response.json();
}
```

---

## 5. SQL

### 5.1 Naming Conventions

```sql
-- Таблицы: snake_case, множественное число
CREATE TABLE instruments (...);
CREATE TABLE market_data (...);

-- Колонки: snake_case
instrument_id UUID NOT NULL;
report_date DATE NOT NULL;

-- Индексы: idx_<table>_<column>
CREATE INDEX idx_market_data_instrument ON market_data(instrument_id);

-- Внешние ключи: fk_<table>_<referenced_table>
ALTER TABLE market_data 
ADD CONSTRAINT fk_market_data_instruments 
FOREIGN KEY (instrument_id) REFERENCES instruments(id);

-- Первичные ключи: <table>_pkey (автоматически)
```

### 5.2 Query Style

```sql
-- Ключевые слова: UPPER CASE
SELECT 
    i.symbol,
    i.name,
    md.close
FROM instruments i
INNER JOIN market_data md ON i.id = md.instrument_id
WHERE 
    i.type = 'CRYPTO'
    AND md.timeframe = '1d'
    AND md.time >= '2020-01-01'
ORDER BY md.time DESC
LIMIT 100;

-- CTE для сложных запросов
WITH recent_signals AS (
    SELECT 
        instrument_id,
        signal_type,
        strength
    FROM signals
    WHERE generated_at >= NOW() - INTERVAL '30 days'
)
SELECT 
    i.symbol,
    rs.signal_type,
    rs.strength
FROM instruments i
INNER JOIN recent_signals rs ON i.id = rs.instrument_id;
```

---

## 6. GIT

### 6.1 Branch Naming

```
main              # Production-ready code
develop           # Development branch
feature/XYZ-123   # Feature branch
bugfix/XYZ-456    # Bug fix branch
hotfix/XYZ-789    # Critical production fix
release/v3.2.0    # Release branch
```

### 6.2 Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Build, CI, etc.

**Examples:**
```
feat(api): add QSpectrum endpoint with MEM support

- Implement QSpectrumRequest/Response DTOs
- Add gRPC client for Python quant service
- Include WFA stability validation

Closes #123
```

```
fix(cot): correct signal direction for GBTC proxy

Signal direction was inverted for GBTC premium signals.
Now using signal_direction = -1 correctly.

Fixes #456
```

---

## 7. ПРОТОКОЛЫ

### 7.1 API Response Format

```json
// Success
{
  "status": "success",
  "data": { ... }
}

// Error
{
  "status": "error",
  "error": {
    "code": "AC001",
    "message": "Minimum years requirement not met",
    "details": { ... }
  }
}
```

### 7.2 Pagination

```json
{
  "status": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 127,
      "pages": 3
    }
  }
}
```

### 7.3 Timestamps

```
// ISO 8601 с timezone
"2026-01-01T10:00:00Z"
"2026-01-01T10:00:00+03:00"

// В БД: TIMESTAMP WITH TIME ZONE
```

---

## 8. КАТЕГОРИИ ЛОГИРОВАНИЯ

| Level | Когда использовать |
|-------|-------------------|
| DEBUG | Детальная информация для отладки |
| INFO | Нормальные операции (запросы, результаты) |
| WARN | Потенциальные проблемы, fallback |
| ERROR | Ошибки, требующие внимания |
| FATAL | Критические ошибки, остановка |

```go
// Go
slog.Debug("processing cycle", "period", period)
slog.Info("signal generated", "symbol", symbol, "type", signalType)
slog.Warn("using cached data", "reason", "provider unavailable")
slog.Error("failed to import data", "error", err)
```

---

**Версия документации:** 3.2 Final
