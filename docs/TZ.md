# ТЕХНИЧЕСКОЕ ЗАДАНИЕ (ТЗ)
## Система циклического анализа и прогнозирования финансовых рынков
### CycleCast v3.2 Final - Методология Ларри Вильямса

---

## 1. ОБЩИЕ СВЕДЕНИЯ

### 1.1 Наименование системы
**CycleCast** — Система циклического анализа и прогнозирования финансовых рынков

### 1.2 Назначение системы
CycleCast предназначена для:
- Моделирования поведения финансовых рынков на основе методологии Ларри Вильямса
- Поиска временных точек разворота рынка через циклический анализ
- Генерации торговых сигналов с подтверждением от «умных денег» (COT или его прокси)
- Валидации прогнозов через исторические аналогии и бэктестинг
- Поддержки традиционных активов и криптовалют (BTC через GBTC/ETF proxy)
- Управления рисками и расчёта размера позиции
- Обеспечения compliance и audit trail для институционального использования

### 1.3 Область применения
| Сегмент | Активы | Особенности |
|---------|--------|-------------|
| TradFi | Акции, фьючерсы, форекс, индексы | 30-50 лет данных, COT отчёты CFTC |
| Crypto | Биткоин, альткоины | 10-15 лет данных, GBTC/ETF proxy вместо COT |
| Hybrid | Смешанные портфели | Агрегация сигналов, кросс-актив корреляции |

### 1.4 Методология Ларри Вильямса (обновлённая v3.2)
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

---

## 2. ТРЕБОВАНИЯ К ФУНКЦИОНАЛЬНОСТИ

### 2.1 Модуль данных рынка (Market Data Module)

#### 2.1.1 Функциональные требования
| ID | Требование | Приоритет | Примечание |
|----|------------|-----------|------------|
| MD-001 | Импорт исторических данных (CSV, JSON, XML) | Критический | |
| MD-002 | Подключение к внешним API (Yahoo, Alpha Vantage, CFTC, Grayscale) | Критический | |
| MD-003 | Хранение OHLCV данных | Критический | |
| MD-004 | Поддержка таймфреймов (1m, 5m, 1h, 1d, 1w, 1M) | Критический | |
| MD-005 | Автоматическое обновление по расписанию | Высокий | Cron + Asynq |
| MD-006 | Нормализация (сплиты, дивиденды, корп. действия) | Критический | |
| MD-007 | Валидация и очистка (пропуски, выбросы) | Критический | |
| MD-008 | Кэширование в Redis | Высокий | |
| MD-009 | Хранение истории: 30-50 лет (TradFi), 10-15 лет (Crypto) | Критический | |
| MD-010 | Синхронизация времени (day_close_utc) | Критический | Для BTC/GBTC корреляции |
| MD-011 | Circuit Breaker для провайдеров | Критический | Graceful degradation |
| MD-012 | Data Freshness мониторинг | Высокий | Алерт если > 4 часа |

#### 2.1.2 Структура данных
```go
type MarketData struct {
    ID              string    `json:"id"`
    Symbol          string    `json:"symbol"`
    Timestamp       time.Time `json:"timestamp"`
    Open            float64   `json:"open"`
    High            float64   `json:"high"`
    Low             float64   `json:"low"`
    Close           float64   `json:"close"`
    Volume          int64     `json:"volume"`
    AdjustedClose   float64   `json:"adjusted_close,omitempty"`
    Timeframe       string    `json:"timeframe"`
    
    // Вычисляемые поля
    NormalizedClose float64 `json:"normalized_close,omitempty"`
    YearDigit       int     `json:"year_digit,omitempty"`
    DetrendedClose  float64 `json:"detrended_close,omitempty"`
    
    // Для крипто-адаптации
    DayCloseUTC     string  `json:"day_close_utc,omitempty"`
}
```

#### 2.1.3 API Endpoints
```
POST   /api/v1/market/import              - Импорт данных
GET    /api/v1/market/symbols             - Список инструментов
GET    /api/v1/market/symbols/{id}        - Данные по инструменту
GET    /api/v1/market/history             - Исторические данные
GET    /api/v1/market/history/aligned     - Данные с синхронизацией времени
DELETE /api/v1/market/symbols/{id}        - Удаление данных
```

---

### 2.2 Модуль Annual Cycle (Сезонность)

#### 2.2.1 Функциональные требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| AC-001 | Загрузка исторических данных (30-50 лет TradFi, 10-15 Crypto) | Критический |
| AC-002 | Детрендинг данных (MA или линейная регрессия) | Критический |
| AC-003 | Расчёт среднего значения для каждого дня года | Критический |
| AC-004 | Нормализация годовых данных к масштабу 0-1 | Критический |
| AC-005 | Расчёт confidence интервалов | Высокий |
| AC-006 | FTE валидация с адаптивным порогом | Критический |

#### 2.2.2 Алгоритм
```go
func CalculateAnnualCycle(prices []MarketData, minYears int) AnnualCycleResult {
    // 1. Проверка минимального количества лет
    if len(uniqueYears(prices)) < minYears {
        return Error("Недостаточно данных")
    }
    
    // 2. Детрендинг
    for year, yearData := range groupByYear(prices) {
        trend := CalculateTrend(yearData)
        detrended[year] = yearData.Close - trend
    }
    
    // 3. Нормализация
    for year, data := range detrended {
        min, max := MinMax(data)
        normalized[year] = (data - min) / (max - min)
    }
    
    // 4. Расчёт среднего по дням года
    for day := 1; day <= 366; day++ {
        values := collectValues(normalized, day)
        avgCycle[day] = Average(values)
        confidence[day] = 1 - (StdDev(values) / Average(values))
    }
    
    return AnnualCycleResult{
        Cycle:      avgCycle,
        Confidence: confidence,
        YearsUsed:  len(uniqueYears(prices)),
        IsValid:    validate(confidence),
    }
}
```

---

### 2.3 Модуль Forward Testing Efficiency (FTE)

#### 2.3.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| FTE-001 | Валидация на out-of-sample данных | Критический |
| FTE-002 | Расчёт корреляции Пирсон | Критический |
| FTE-003 | Детекция "сломанных" сезонностей | Критический |
| FTE-004 | Walk-Forward тестирование | Критический |
| FTE-005 | Адаптивный порог на realised volatility | Критический |

#### 2.3.2 Алгоритм
```go
func ValidateFTE(prices []MarketData, model AnnualCycle, config FTEConfig) FTEResult {
    // Разделение 70/30
    splitPoint := len(prices) * 0.7
    inSample := prices[:splitPoint]
    outSample := prices[splitPoint:]
    
    // Прогноз
    prediction := Project(model, len(outSample))
    
    // Корреляция
    correlation := PearsonCorrelation(prediction, outSample.Close)
    
    // Адаптивный порог
    threshold := calculateAdaptiveThreshold(prices, config)
    
    return FTEResult{
        Correlation: correlation,
        IsValid:     correlation > threshold,
        Status:      getStatus(correlation, threshold),
    }
}

func calculateAdaptiveThreshold(prices []MarketData, config FTEConfig) float64 {
    currentVol := calculateRealizedVol(prices, 30)
    longTermVol := calculateRealizedVol(prices, 252)
    
    ratio := currentVol / longTermVol
    threshold := config.BaseThreshold * (1 + config.SensitivityLambda * (ratio - 1))
    
    return math.Max(threshold, config.BaseThreshold * 0.5)
}
```

---

### 2.4 Модуль QSpectrum (Python-сервис)

#### 2.4.1 Требования
| ID | Требование | Приоритет | Примечание |
|----|------------|-----------|------------|
| QS-001 | Циклическая корреляция (не FFT!) | Критический | Go или Python |
| QS-002 | Вычисление энергии цикла | Критический | |
| QS-003 | МЭМ (Burg's method) | Критический | **Только Python** |
| QS-004 | Выбор 3 доминантных циклов | Критический | |
| QS-005 | Walk-Forward Analysis | Критический | |
| QS-006 | gRPC интеграция с Go | Критический | Unary call |

#### 2.4.2 Архитектура
```
┌─────────────────┐      gRPC      ┌─────────────────┐
│   Go Backend    │ ◄────────────► │  Python Quant   │
│   (API, DB)     │                │   (Math, ML)    │
└─────────────────┘                └─────────────────┘
        │                                  │
        ▼                                  ▼
  PostgreSQL                         NumPy, SciPy
  TimescaleDB                        Statsmodels
  Redis                              scikit-learn
```

#### 2.4.3 Формулы
```
1. Циклическая корреляция:
   CyclicCorrelation(period) = Σ(t=period to N) [P(t) × P(t-period)] / (N - period)

2. Энергия цикла:
   Energy(period) = |CyclicCorrelation| × √(N/period) × WFA_Stability

3. МЭМ (Burg's method):
   P(f) = σ² / |1 + Σ(k=1 to p) aₖ × e^(-i2πfk)|²

4. WFA Stability:
   WFA_Stability = Count(Correlation > 0) / Total_Periods
```

---

### 2.5 Модуль Composite Line

#### 2.5.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| CL-001 | Наложение 3 волн (short/medium/long) | Критический |
| CL-002 | Детекция точек резонанса | Критический |
| CL-003 | Генерация сигналов BUY/SELL | Критический |
| CL-004 | Прогноз на N дней вперёд | Критический |

#### 2.5.2 Формула
```
CL(t) = A₁sin(2πf₁t + φ₁) + A₂sin(2πf₂t + φ₂) + A₃sin(2πf₃t + φ₃)

Сигналы:
- BUY:  все 3 цикла направлены вверх (производная > 0)
- SELL: все 3 цикла направлены вниз (производная < 0)
```

---

### 2.6 Модуль Decennial Patterns

#### 2.6.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| DP-001 | Группировка по yearDigit (0-9) | Критический |
| DP-002 | Нормализация 0-1 | Критический |
| DP-003 | Расчёт усреднённого паттерна | Критический |
| DP-004 | Корреляция с текущим годом | Критический |
| DP-005 | Отключение для crypto (< 30 лет) | Высокий |

#### 2.6.2 Формула
```
DP(digit, day) = Average(NormalizedPrice) for years where year%10 == digit
```

---

### 2.7 Модуль Phenomenological Model (Python-сервис)

#### 2.7.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| PM-001 | DTW (Dynamic Time Warping) | Критический |
| PM-002 | Фильтр по Decennial (yearDigit) | Критический |
| PM-003 | Training Interval | Критический |
| PM-004 | Best Matches Ranking | Критический |
| PM-005 | Проекция продолжения | Критический |
| PM-006 | Гибридная оптимизация (filter + exact) | Критический |

#### 2.7.2 Алгоритм DTW (гибридный)
```python
def adaptive_dtw(target, history, config):
    # 1. Грубая фильтрация: корреляция > 0.6 (O(N))
    candidates = fast_correlation_filter(target, history, threshold=0.6)
    
    # 2. Ограничение топ-100
    if len(candidates) > 100:
        candidates = candidates[:100]
    
    # 3. Параллельный exact DTW
    results = Parallel(n_jobs=-1)(
        delayed(exact_dtw)(target, h) for h in candidates
    )
    
    return sorted(results, key=lambda x: x.distance)
```

---

### 2.8 Модуль COT/GBTC Analysis

#### 2.8.1 Требования
| ID | Требование | Приоритет | Примечание |
|----|------------|-----------|------------|
| COT-001 | Импорт отчётов CFTC COT | Критический | TradFi |
| COT-002 | Парсинг GBTC/ETF данных | Критический | **Crypto** |
| COT-003 | Анализ Commercials / Premium | Критический | |
| COT-004 | Расчёт COT/GBTC Index (0-100) | Критический | |
| COT-005 | Детекция экстремумов (>80, <20) | Критический | |
| COT-006 | Поддержка signal_direction (-1 для GBTC) | Критический | **Новое** |
| COT-007 | Учёт regime_change_date (2024-01-11) | Критический | **Новое** |
| COT-008 | Robust нормализация (Percentile Rank) | Критический | **Новое** |
| COT-009 | Autocorrelation Filter (min 21 день) | Критический | **Новое** |
| COT-010 | Liquidity-Weighted Aggregation | Высокий | **Новое** |

#### 2.8.2 Структура данных
```go
type COTData struct {
    ID              string    `json:"id"`
    Symbol          string    `json:"symbol"`
    ReportDate      time.Time `json:"report_date"`
    
    // Позиции (для фьючерсов)
    Commercials     COTPosition `json:"commercials"`
    LargeSpecs      COTPosition `json:"large_specs"`
    SmallSpecs      COTPosition `json:"small_specs"`
    
    // Для трастов/ETF (GBTC)
    Premium         float64   `json:"premium,omitempty"`
    NAV             float64   `json:"nav,omitempty"`
    
    // Индексы
    CommercialIndex float64   `json:"commercial_index"`
    NetPosition     int64     `json:"net_position"`
    
    // Сигналы
    IsExtreme       bool      `json:"is_extreme"`
    SignalType      string    `json:"signal_type,omitempty"`
}
```

#### 2.8.3 Формула GBTC Index
```
GBTC_Index = PercentileRank(Current_Premium, Window_N)

Сигналы (signal_direction = -1):
- GBTC_Index > 80: BEARISH (эйфория, институты продают)
- GBTC_Index < 20: BULLISH (паника, институты покупают)

Robust нормализация (Percentile Rank):
PR(X) = Count(x_i < X) / N × 100%
```

---

### 2.9 Модуль Risk Management

#### 2.9.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| RM-001 | Расчёт размера позиции (Position Sizing) | Критический |
| RM-002 | Stop-Loss расчёт | Критический |
| RM-003 | Take-Profit расчёт | Критический |
| RM-004 | Max Drawdown лимит | Критический |
| RM-005 | Kelly Criterion / Fixed Fractional | Высокий |
| RM-006 | Signal Decay Function | Критический |

#### 2.9.2 Алгоритм
```go
func CalculatePosition(signal Signal, account Balance, risk RiskConfig) Position {
    // Risk per trade (например, 2% от капитала)
    riskAmount := account.Balance * risk.PerTradePercent
    
    // Stop-Loss расстояние
    stopDistance := abs(signal.EntryPrice - signal.StopLoss)
    
    // Размер позиции
    positionSize := riskAmount / stopDistance
    
    // Signal Decay
    effectiveStrength := signal.InitialStrength * math.Pow(0.5, float64(signal.AgeDays) / float64(signal.HalfLifeDays))
    
    // Проверка на Max Drawdown
    if account.CurrentDrawdown > risk.MaxDrawdown {
        return Position{Size: 0, Reason: "Max Drawdown exceeded"}
    }
    
    return Position{
        Size:       positionSize,
        Entry:      signal.EntryPrice,
        StopLoss:   signal.StopLoss,
        TakeProfit: signal.TakeProfit,
        Strength:   effectiveStrength,
    }
}
```

---

### 2.10 Модуль Backtesting Engine

#### 2.10.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| BT-001 | Симуляция торговли на истории | Критический |
| BT-002 | Учёт комиссий и проскальзывания | Критический |
| BT-003 | In-Sample / Out-of-Sample разделение | Критический |
| BT-004 | Генерация Equity Curve | Критический |
| BT-005 | Метрики (Sharpe, MaxDD, WinRate) | Критический |
| BT-006 | Walk-Forward оптимизация | Критический |
| BT-007 | Bootstrap для доверительных интервалов | Критический |

#### 2.10.2 Метрики
```
- Total Return (%)
- CAGR (%)
- Sharpe Ratio
- Max Drawdown (%)
- Win Rate (%)
- Profit Factor
- Expectancy
- Bootstrap CI (95%)
```

#### 2.10.3 Правило
```
⚠️ НЕТ БЭКТЕСТА → НЕТ СИГНАЛА В ПРОДАКШЕНЕ
```

---

### 2.11 Модуль Qualified Trend Break (QTB)

#### 2.11.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| QTB-001 | Детекция пробоев трендовых линий | Критический |
| QTB-002 | Фильтрация через Composite Line | Критический |
| QTB-003 | Генерация сигналов Confirm / False | Критический |

#### 2.11.2 Логика
```
QTB = Confirm если:
  - Цена пробивает трендовую линию
  - И Composite Line направлен в ту же сторону

QTB = False если:
  - Цена пробивает уровень
  - Но Composite Line направлен в противоположную сторону
```

---

### 2.12 Модуль Data Lineage & Audit

#### 2.12.1 Требования
| ID | Требование | Приоритет |
|----|------------|-----------|
| DL-001 | Traceability каждого сигнала | Критический |
| DL-002 | Версия кода (git commit) | Критический |
| DL-003 | Исходные данные (hash) | Критический |
| DL-004 | Параметры моделей | Критический |
| DL-005 | Audit logging | Критический |

#### 2.12.2 Структура
```go
type DataLineage struct {
    SignalID        uuid.UUID           `json:"signal_id"`
    SourceData      []DataSource        `json:"source_data"`
    Transformations []Transform         `json:"transformations"`
    Parameters      map[string]float64  `json:"parameters"`
    CodeVersion     string              `json:"code_version"`
    Timestamp       time.Time           `json:"timestamp"`
    Checksum        string              `json:"checksum"`
}
```

---

### 2.13 Модуль интеграции (Workflow)

#### 2.13.1 Итоговый алгоритм
```go
func WilliamsWorkflow(config WorkflowConfig) WorkflowResult {
    // Шаг 0: Backtest (только для новых стратегий)
    if config.RequireBacktest {
        btResult := RunBacktest(config)
        if !btResult.IsProfitable {
            return WorkflowResult{Status: "BACKTEST_FAILED"}
        }
    }
    
    // Шаг 1: Annual Cycle
    activeAssets := selectAssetsBySeasonality(config)
    
    // Шаг 2: Decennial
    currentYearDigit := time.Now().Year() % 10
    
    // Шаг 3: Composite Line (через Python)
    for i := range activeAssets {
        cycles := pythonService.QSpectrum(activeAssets[i].Prices)
        activeAssets[i].Composite = GenerateCompositeLine(cycles.Top3)
    }
    
    // Шаг 4: Phenomenological (через Python)
    for i := range activeAssets {
        activeAssets[i].Phenom = pythonService.PhenomSearch(activeAssets[i].Prices)
    }
    
    // Шаг 5: COT/GBTC
    for i := range activeAssets {
        activeAssets[i].COT = AnalyzeCOT(activeAssets[i].Symbol)
    }
    
    // Шаг 6: Risk Management
    for i := range activeAssets {
        activeAssets[i].Position = CalculatePosition(...)
    }
    
    // Шаг 7: Statistical Validation
    for i := range activeAssets {
        activeAssets[i].Stats = CalculateStatistics(...)
    }
    
    // Шаг 8: Data Lineage
    for i := range activeAssets {
        SaveLineage(activeAssets[i])
    }
    
    // Шаг 9: Сигналы
    signals := generateSignals(activeAssets)
    
    return WorkflowResult{
        ActiveAssets: activeAssets,
        Signals:      signals,
        Status:       "SUCCESS",
    }
}
```

---

## 3. ТРЕБОВАНИЯ К ИНТЕРФЕЙСУ

### 3.1 Web Interface
- **Dashboard:** Активные активы, сигналы, COT статус
- **Charts:** OHLC + Composite Line + Projection
- **Analysis Panel:** Параметры алгоритмов, результаты
- **Backtest Report:** Equity curve, метрики, bootstrap CI
- **Audit Trail:** Data lineage viewer

### 3.2 API
- REST API (OpenAPI 3.0)
- gRPC (Protocol Buffers 3)
- WebSocket (RFC 6455)

---

## 4. ТРЕБОВАНИЯ К БЕЗОПАСНОСТИ

| ID | Требование |
|----|------------|
| SEC-001 | JWT токены для API |
| SEC-002 | Ролевая модель (Admin, Analyst, Viewer) |
| SEC-003 | Rate limiting |
| SEC-004 | HTTPS обязательно |
| SEC-005 | Шифрование API-ключей (HashiCorp Vault) |
| SEC-006 | Аудит логов |
| SEC-007 | Резервное копирование БД |
| SEC-008 | Data Lineage для compliance |

---

## 5. ТРЕБОВАНИЯ К ПРОИЗВОДИТЕЛЬНОСТИ

| Метрика | Требование |
|---------|------------|
| API Response Time | < 100ms (p95) |
| Annual Cycle расчёт | < 200ms |
| Composite Line генерация | < 100ms |
| Python gRPC call | < 500ms |
| WebSocket latency | < 10ms |
| Concurrent users | 1000+ |
| Data points stored | 100M+ |

---

## 6. ТРЕБОВАНИЯ К НАДЁЖНОСТИ

| Метрика | Требование |
|---------|------------|
| Uptime | 99.9% |
| RTO | < 1 hour |
| RPO | < 1 hour |
| Error rate | < 0.1% |

---

## 7. ПРИЁМОЧНЫЕ ИСПЫТАНИЯ

### 7.1 Функциональные тесты
| ID | Тест | Критерий |
|----|------|----------|
| AT-001 | Импорт 1M+ точек | < 60 сек |
| AT-002 | Annual Cycle | Корректная кривая |
| AT-003 | FTE валидация | Детекция сломанных |
| AT-004 | Composite Line | Детекция резонанса |
| AT-005 | Backtest Engine | Equity curve > 0 |
| AT-006 | COT/GBTC | Корректный индекс |
| AT-007 | Risk Management | Позиция рассчитана |
| AT-008 | Statistical Validation | p-value < 0.05 |
| AT-009 | Data Lineage | Полная traceability |

### 7.2 Нагрузочные тесты
| ID | Тест | Критерий |
|----|------|----------|
| LT-001 | 1000 API запросов | Response < 200ms |
| LT-002 | 1000 WebSocket | Latency < 20ms |
| LT-003 | 24h continuous | Uptime > 99.9% |

### 7.3 Chaos Engineering тесты
| ID | Тест | Критерий |
|----|------|----------|
| CT-001 | Python service failure | Go degrades gracefully |
| CT-002 | Redis failure | Fallback to PostgreSQL |
| CT-003 | API load spike | Rate limiting activates |
| CT-004 | Database latency | Circuit breaker opens |
| CT-005 | Network partition | gRPC retry logic works |

---

## 8. ИТОГОВЫЙ АЛГОРИТМ ЛАРРИ ВИЛЬЯМСА ДЛЯ БИТКОИНА

```
1. Annual Cycle (BTC, 15 лет) с FTE-валидацией по адаптивному порогу.
2. Decennial Patterns (BTC, текущий year digit) — опционально.
3. Composite Line (BTC) через QSpectrum.
4. Phenomenological Model (BTC) с гибридным DTW.
5. COT (GBTC + другие прокси):
   - Загрузить данные GBTC (цена, NAV)
   - Рассчитать премию
   - Применить regime_change_date (использовать данные только после 2024-01-11)
   - Рассчитать процентильный индекс за 26 недель
   - Интерпретировать с signal_direction = -1
   - Применить фильтр автокорреляции (min_signal_distance)
   - При наличии нескольких прокси – взвешенное усреднение
6. Qualified Trend Break (BTC)
7. Risk Management (позиция, stop-loss, take-profit)
8. Statistical Validation (p-value, Bootstrap CI)
9. Data Lineage (audit trail)
10. Итоговый сигнал: совпадение направлений Composite Line, COT-сигнала, Phenom и QTB.
```

---

**Версия документации:** 3.2 Final  
**Статус:** ✅ УТВЕРЖДЕНО К РАЗРАБОТКЕ
