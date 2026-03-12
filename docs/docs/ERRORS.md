# ERRORS

> **Версия:** 3.2 Final | **CycleCast API Error Codes**

---

## СТРУКТУРА ОТВЕТА С ОШИБКОЙ

```json
{
  "status": "error",
  "error": {
    "code": "AC001",
    "message": "Minimum years requirement not met",
    "details": {
      "required_years": 10,
      "actual_years": 5
    },
    "timestamp": "2026-01-01T10:00:00Z",
    "request_id": "uuid"
  }
}
```

---

## HTTP STATUS CODES

| Status | Значение | Когда использовать |
|--------|----------|-------------------|
| 200 | OK | Успешный запрос |
| 201 | Created | Ресурс создан |
| 204 | No Content | Успех без тела ответа |
| 400 | Bad Request | Неверный формат запроса |
| 401 | Unauthorized | Требуется авторизация |
| 403 | Forbidden | Нет прав доступа |
| 404 | Not Found | Ресурс не найден |
| 409 | Conflict | Конфликт (дубликат) |
| 422 | Unprocessable Entity | Ошибка валидации |
| 429 | Too Many Requests | Rate limit |
| 500 | Internal Server Error | Внутренняя ошибка |
| 502 | Bad Gateway | Upstream ошибка |
| 503 | Service Unavailable | Сервис недоступен |
| 504 | Gateway Timeout | Timeout upstream |

---

## КОДЫ ОШИБОК ПО МОДУЛЯМ

### MD - Market Data (MD001-MD099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| MD001 | Insufficient historical data | 400 | Недостаточно исторических данных | Загрузите больше данных |
| MD002 | Invalid timeframe | 400 | Неверный таймфрейм | Используйте: 1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M |
| MD003 | Data gap detected | 400 | Обнаружен пропуск данных > 5 дней | Заполните пропуски или используйте другой источник |
| MD004 | Invalid date range | 400 | Неверный диапазон дат | start_date < end_date |
| MD005 | Symbol not found | 404 | Инструмент не найден | Проверьте символ |
| MD006 | Import failed | 500 | Ошибка импорта данных | Проверьте формат файла |
| MD007 | Provider unavailable | 503 | Провайдер данных недоступен | Попробуйте позже или используйте fallback |
| MD008 | Rate limit exceeded (provider) | 429 | Превышен лимит провайдера | Подождите или используйте API key |
| MD009 | Invalid OHLCV data | 400 | Неверные OHLCV данные | high >= low, high >= open/close |
| MD010 | Duplicate data points | 409 | Дубликаты данных | Используйте upsert |

---

### AC - Annual Cycle (AC001-AC099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| AC001 | Minimum years not met | 400 | Минимум лет не достигнут | Требуется >= min_years данных |
| AC002 | FTE validation failed | 422 | FTE валидация не пройдена | Модель не валидна на out-of-sample |
| AC003 | Detrending failed | 500 | Ошибка детрендинга | Проверьте данные |
| AC004 | Normalization failed | 500 | Ошибка нормализации | Проверьте данные на NaN/Inf |
| AC005 | Confidence calculation failed | 500 | Ошибка расчёта confidence | Недостаточно вариативности |
| AC006 | Invalid year_digit | 400 | Неверный year_digit | Должен быть 0-9 или null |
| AC007 | Seasonality broken | 422 | Сезонность сломана | FTE < threshold |
| AC008 | Adaptive threshold calculation failed | 500 | Ошибка расчёта адаптивного порога | Проверьте volatility data |

---

### QS - QSpectrum (QS001-QS099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| QS001 | No dominant cycles found | 422 | Доминантные циклы не найдены | Уменьшите energy_threshold |
| QS002 | Invalid period range | 400 | Неверный диапазон периодов | min_period < max_period < N/2 |
| QS003 | MEM calculation failed | 500 | Ошибка MEM | Уменьшите mem_order |
| QS004 | WFA stability too low | 422 | Низкая WFA stability | Циклы нестабильны |
| QS005 | Insufficient data for spectrum | 400 | Недостаточно данных | Требуется >= 3×max_period |
| QS006 | Convergence not reached | 500 | MEM не сошёлся | Проверьте данные на стационарность |
| QS007 | Python service unavailable | 503 | Python Quant недоступен | Проверьте gRPC connection |

---

### CL - Composite Line (CL001-CL099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| CL001 | Less than 3 cycles available | 422 | Меньше 3 циклов | Сначала запустите QSpectrum |
| CL002 | Cycle not found | 404 | Цикл не найден | Проверьте cycle_id |
| CL003 | Resonance calculation failed | 500 | Ошибка расчёта резонанса | Проверьте фазы циклов |
| CL004 | Projection failed | 500 | Ошибка проекции | Неверные параметры |
| CL005 | U-Turn detection failed | 500 | Ошибка детекции U-Turn | Недостаточно истории |

---

### PH - Phenomenological (PH001-PH099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| PH001 | No matching patterns found | 422 | Нет совпадающих паттернов | Уменьшите correlation_threshold |
| PH002 | DTW calculation failed | 500 | Ошибка DTW | Проверьте данные |
| PH003 | Training interval too short | 400 | Training interval слишком короткий | Увеличьте training_interval |
| PH004 | Decennial filter too strict | 422 | Decennial filter слишком строгий | Отключите или расширьте |
| PH005 | Insufficient historical patterns | 422 | Недостаточно исторических паттернов | Нужно больше данных |

---

### COT - COT/GBTC (COT001-COT099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| COT001 | COT data not available | 404 | COT данные недоступны | Проверьте символ или дату |
| COT002 | Invalid proxy configuration | 400 | Неверная конфигурация прокси | Проверьте proxy_list |
| COT003 | Premium calculation failed | 500 | Ошибка расчёта премии | Проверьте NAV и price |
| COT004 | Percentile rank window too small | 400 | Окно Percentile Rank слишком маленькое | Увеличьте window_weeks |
| COT005 | Regime change date invalid | 400 | Неверная дата regime change | Проверьте формат даты |
| COT006 | Signal clustering detected | 422 | Обнаружен кластер сигналов | Примените autocorrelation filter |
| COT007 | Liquidity data missing | 400 | Отсутствуют данные о ликвидности | Нужны volume/AUM |
| COT008 | Invalid signal direction | 400 | Неверный signal_direction | Должен быть 1 или -1 |

---

### BT - Backtest (BT001-BT099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| BT001 | Backtest failed | 500 | Бэктест завершился с ошибкой | Проверьте логи |
| BT002 | Negative equity | 422 | Отрицательный equity | Уменьшите position size |
| BT003 | No trades generated | 422 | Нет сделок | Проверьте параметры стратегии |
| BT004 | Bootstrap failed | 500 | Ошибка Bootstrap | Уменьшите iterations |
| BT005 | In-sample validation failed | 422 | IS валидация не пройдена | Стратегия не работает |
| BT006 | Out-of-sample validation failed | 422 | OOS валидация не пройдена | Переобучение |
| BT007 | Max drawdown exceeded | 422 | Превышен max drawdown | Стратегия слишком рискованная |
| BT008 | Sharpe ratio too low | 422 | Sharpe ratio слишком низкий | Стратегия неэффективна |
| BT009 | Insufficient data for backtest | 400 | Недостаточно данных | Нужно больше истории |

---

### RM - Risk Management (RM001-RM099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| RM001 | Max drawdown exceeded | 403 | Превышен максимальный drawdown | Нет новых позиций |
| RM002 | Invalid stop loss | 400 | Неверный stop-loss | stop_loss != entry_price |
| RM003 | Invalid take profit | 400 | Неверный take-profit | Проверьте логику |
| RM004 | Position size calculation failed | 500 | Ошибка расчёта позиции | Проверьте параметры |
| RM005 | Risk per trade exceeded | 403 | Превышен риск на сделку | Уменьшите размер |
| RM006 | Signal expired | 410 | Сигнал истёк | Возраст > half_life × 3 |

---

### LN - Lineage (LN001-LN099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| LN001 | Lineage verification failed | 500 | Верификация не пройдена | Checksum mismatch |
| LN002 | Signal not found | 404 | Сигнал не найден | Проверьте signal_id |
| LN003 | Source data hash mismatch | 500 | Hash исходных данных не совпадает | Данные изменены |
| LN004 | Transformation chain broken | 500 | Цепочка трансформаций нарушена | Проверьте hashes |
| LN005 | Export failed | 500 | Ошибка экспорта | Проверьте формат |

---

### AU - Auth (AU001-AU099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| AU001 | Invalid token | 401 | Неверный токен | Обновите токен |
| AU002 | Token expired | 401 | Токен истёк | Обновите токен |
| AU003 | Invalid API key | 401 | Неверный API ключ | Проверьте ключ |
| AU004 | Insufficient permissions | 403 | Недостаточно прав | Обратитесь к админу |
| AU005 | User not found | 404 | Пользователь не найден | Проверьте email |
| AU006 | Invalid credentials | 401 | Неверные учётные данные | Проверьте логин/пароль |
| AU007 | Account locked | 403 | Аккаунт заблокирован | Обратитесь к админу |

---

### SY - System (SY001-SY099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| SY001 | Internal server error | 500 | Внутренняя ошибка | Попробуйте позже |
| SY002 | Service unavailable | 503 | Сервис недоступен | Попробуйте позже |
| SY003 | Rate limit exceeded | 429 | Превышен rate limit | Попробуйте через минуту |
| SY004 | Request timeout | 504 | Timeout запроса | Уменьшите объём данных |
| SY005 | Invalid request format | 400 | Неверный формат | Проверьте JSON |
| SY006 | Request too large | 413 | Запрос слишком большой | Уменьшите размер |
| SY007 | Maintenance mode | 503 | Режим обслуживания | Попробуйте позже |
| SY008 | Feature not enabled | 403 | Функция отключена | Обратитесь к админу |

---

### DB - Database (DB001-DB099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| DB001 | Connection failed | 503 | Ошибка подключения к БД | Попробуйте позже |
| DB002 | Query timeout | 504 | Timeout запроса | Оптимизируйте запрос |
| DB003 | Constraint violation | 409 | Нарушение constraint | Проверьте уникальность |
| DB004 | Transaction failed | 500 | Ошибка транзакции | Попробуйте снова |
| DB005 | Migration required | 503 | Требуется миграция | Запустите миграции |

---

### VT - Validation (VT001-VT099)

| Code | Message | HTTP | Description | Solution |
|------|---------|------|-------------|----------|
| VT001 | Required field missing | 400 | Обязательное поле отсутствует | Добавьте поле |
| VT002 | Invalid format | 400 | Неверный формат | Проверьте формат |
| VT003 | Value out of range | 400 | Значение вне диапазона | Проверьте min/max |
| VT004 | Invalid enum value | 400 | Неверное значение enum | Проверьте допустимые значения |
| VT005 | Date format invalid | 400 | Неверный формат даты | Используйте ISO 8601 |
| VT006 | UUID format invalid | 400 | Неверный формат UUID | Проверьте UUID |

---

## ОБРАБОТКА ОШИБОК В КОДЕ

### Go Backend

```go
// Определение ошибки
var ErrInsufficientData = &Error{
    Code:    "MD001",
    Message: "Insufficient historical data",
}

// Использование
if len(prices) < minRequired {
    return nil, ErrInsufficientData.WithDetails(map[string]any{
        "required_years": minYears,
        "actual_years":   len(uniqueYears(prices)),
    })
}

// Response
c.JSON(http.StatusBadRequest, ErrorResponse{
    Status: "error",
    Error: ErrorDetail{
        Code:      "MD001",
        Message:   "Insufficient historical data",
        Details:   details,
        Timestamp: time.Now(),
        RequestID: c.GetString("request_id"),
    },
})
```

### Python Quant

```python
class CycleCastError(Exception):
    """Base exception for CycleCast."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class InsufficientDataError(CycleCastError):
    def __init__(self, required: int, actual: int):
        super().__init__(
            code="MD001",
            message="Insufficient historical data",
            details={"required_years": required, "actual_years": actual}
        )

# Usage
if len(prices) < min_required:
    raise InsufficientDataError(min_years, len(prices))
```

---

## ЛОГИРОВАНИЕ ОШИБОК

```go
slog.Error("request failed",
    "code", err.Code,
    "message", err.Message,
    "details", err.Details,
    "request_id", requestID,
    "stack_trace", debug.Stack(),
)
```

---

**Версия документации:** 3.2 Final
