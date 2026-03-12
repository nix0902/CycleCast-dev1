# GLOSSARY

> **Версия:** 3.2 Final | **CycleCast Project**

---

## A

### Annual Cycle (Сезонность)
Паттерн, показывающий типичное поведение цены в течение календарного года. Рассчитывается как среднее нормализованных цен для каждого дня года за исторический период.

**Формула:**
```
AC(day) = Σ NormalizedPrice(year, day) / N
```

**Пороги данных:** TradFi: 30-50 лет, Crypto: 10-15 лет

---

### Adaptive Threshold (Адаптивный порог)
Динамический порог для FTE валидации, учитывающий текущую волатильность.

**Формула:**
```
threshold = base × (1 + λ × (current_vol / long_term_vol - 1))
```

Где λ = 0.5 (sensitivity parameter)

---

## B

### Bootstrap CI (Bootstrap Confidence Interval)
Метод оценки доверительных интервалов путём многократного ресемплирования данных с заменой.

**Параметры:** 1000 итераций, 95% confidence level

**Результат:** `[ci_lower, ci_upper]` + `p_value`

---

### Burg's MEM (Maximum Entropy Method)
Метод спектрального анализа, разработанный John Parker Burg. Используется для оценки спектральной плотности мощности нестационарных временных рядов.

**Преимущества перед FFT:**
- Работает с короткими рядами
- Лучшее разрешение по частоте
- Подходит для нестационарных данных

**Формула:**
```
P(f) = σ² / |1 + Σ(k=1 to p) aₖ × e^(-i2πfk)|²
```

---

## C

### COT (Commitment of Traders)
Еженедельный отчёт CFTC, показывающий позиции крупных участников рынка.

**Группы:**
- **Commercials (Хеджеры)** — производители/потребители, считаются "умными деньгами"
- **Large Speculators** — фонды, CTAs
- **Small Speculators** — ритейл трейдеры

**COT Index:**
```
COT_Index = (Current_Net - Min_N) / (Max_N - Min_N) × 100
```

---

### Composite Line
Наложение трёх доминантных циклов для прогнозирования направления цены.

**Формула:**
```
CL(t) = A₁sin(2πf₁t + φ₁) + A₂sin(2πf₂t + φ₂) + A₃sin(2πf₃t + φ₃)
```

**Сигналы:**
- BUY: все 3 цикла направлены вверх (производная > 0)
- SELL: все 3 цикла направлены вниз (производная < 0)

---

### Cyclic Correlation (Циклическая корреляция)
Метод выявления циклов путём корреляции цены с её лаговой копией.

**Формула:**
```
C(period) = Σ(t=period to N) [P(t) × P(t-period)] / (N - period)
```

**Отличие от FFT:** Работает напрямую с ценами, не требует стационарности.

---

## D

### Data Lineage
Полная история происхождения данных и трансформаций для каждого сигнала.

**Компоненты:**
- Source Data (источники)
- Transformations (трансформации)
- Parameters (параметры моделей)
- Code Version (версия кода)
- Checksum (контрольная сумма)

---

### Decennial Patterns (Десятилетние паттерны)
Паттерны, сгруппированные по последней цифре года (0-9).

**Формула:**
```
DP(digit, day) = Average(NormalizedPrice) for years where year%10 == digit
```

**Пример:** Для 2026 года используется паттерн года 6 (2006, 1996, 1986...)

---

### DTW (Dynamic Time Warping)
Алгоритм измерения схожести между временными рядами разной длины.

**Гибридный подход:**
1. Грубая фильтрация: корреляция > 0.6 (O(N))
2. Ограничение топ-100 кандидатов
3. Параллельный exact DTW

---

### Detrending (Детрендинг)
Удаление долгосрочного тренда из данных перед анализом циклов.

**Методы:**
- MA (скользящая средняя)
- Linear Regression
- HP Filter

---

## E

### Energy (Энергия цикла)
Мера значимости цикла.

**Формула:**
```
Energy(period) = |CyclicCorrelation| × √(N/period) × WFA_Stability
```

---

## F

### FTE (Forward Testing Efficiency)
Метрика валидации прогнозной способности модели на out-of-sample данных.

**Формула:**
```
FTE = PearsonCorrelation(Projection, Actual)
```

**Пороги:**
- TradFi: FTE > 0.0 (базовый) или адаптивный
- Crypto: FTE > 0.08 (базовый) или адаптивный

---

## G

### GBTC Proxy
Метод использования премии/дисконта GBTC как прокси для "умных денег" в биткоине.

**Особенности:**
- `signal_direction = -1` (инверсия сигнала)
- `regime_change_date = 2024-01-11` (ETF конвертация)
- Percentile Rank вместо min-max нормализации

**Интерпретация:**
- Premium high (> 80th percentile) → BEARISH (эйфория)
- Premium low (< 20th percentile) → BULLISH (паника)

---

## H

### Half-Life (Период полураспада)
Время, за которое сила сигнала уменьшается вдвое.

**Default:** 14 дней

---

## I

### In-Sample / Out-of-Sample
Разделение данных для обучения и тестирования.

**Default:** 70% In-Sample / 30% Out-of-Sample

---

## L

### Liquidity-Weighted Aggregation
Метод объединения сигналов от нескольких прокси с весами пропорциональными ликвидности.

**Формула:**
```
Index_final = Σ(w_i × Index_i) / Σw_i
где w_i = Volume_i × AUM_i
```

---

## M

### MEM (Maximum Entropy Method)
См. Burg's MEM

---

## N

### Normalization (Нормализация)
Приведение данных к единому масштабу.

**Методы:**
- Min-Max: `(x - min) / (max - min)`
- Percentile Rank: `PR(X) = Count(x_i < X) / N × 100%` (robust)
- Z-Score: `(x - μ) / σ`

---

## P

### Percentile Rank
Robust метод нормализации, устойчивый к выбросам.

**Формула:**
```
PR(X) = Count(x_i < X) / N × 100%
```

**Используется для:** GBTC Index

---

### Phenomenological Model
Метод поиска исторических аналогий для прогнозирования.

**Компоненты:**
- DTW для схожести
- Decennial Filter по yearDigit
- Training Interval
- Projection

---

### P-value
Вероятность получить результат не хуже наблюдаемого при нулевой гипотезе.

**Порог:** p < 0.05 считается статистически значимым.

---

### Position Sizing
Расчёт размера позиции на основе риска.

**Формула:**
```
Position Size = Risk Amount / Stop Distance
Risk Amount = Account × PerTradePercent × SignalStrength
```

---

## Q

### QSpectrum
Метод спектрального анализа, разработанный для финансовых рынков.

**Отличия от FFT:**
- Использует циклическую корреляцию
- Интегрирован с MEM
- Walk-Forward Stability validation

---

### QTB (Qualified Trend Break)
Метод подтверждения пробоев трендовых линий через Composite Line.

**Логика:**
- Confirm: цена пробивает + Composite Line в ту же сторону
- False: цена пробивает + Composite Line в противоположную сторону

---

## R

### Regime Change Date
Дата структурного изменения в данных инструмента.

**Пример:** GBTC → ETF конвертация 2024-01-11

**Обработка:** Использовать только данные после regime_change_date

---

### Resonance (Резонанс)
Точка, где все три цикла Composite Line направлены в одну сторону.

**Типы:**
- BUY Resonance: все циклы направлены вверх
- SELL Resonance: все циклы направлены вниз

---

## S

### Signal Decay
Уменьшение силы сигнала со временем.

**Формула:**
```
Effective_Strength = Initial × 0.5^(AgeDays / HalfLifeDays)
```

---

### Sharpe Ratio
Мера доходности с учётом риска.

**Формула:**
```
Sharpe = (Return - RiskFreeRate) / StdDev × √252
```

**Цель:** Sharpe > 1.0

---

### Signal Direction
Направление интерпретации сигнала COT.

**Значения:**
- `+1`: Прямая (Commercials покупают → BULLISH)
- `-1`: Инверсная (GBTC premium high → BEARISH)

---

## T

### TradFi (Traditional Finance)
Традиционные финансовые инструменты: акции, фьючерсы, форекс, товары.

**Особенности:**
- 30-50 лет исторических данных
- COT отчёты CFTC
- FTE threshold = 0.05

---

## U

### U-Turn
Точка разворота Composite Line.

**Детекция:**
- Local minimum → BOTTOM U-Turn
- Local maximum → TOP U-Turn

---

## W

### WFA (Walk-Forward Analysis)
Метод валидации устойчивости циклов путём многократного разделения данных.

**Метрика:**
```
WFA_Stability = Count(Correlation > 0) / Total_Periods
```

---

### Williams Methodology
Методология Ларри Вильямса для анализа рынков.

**Шаги (v3.2):**
1. Backtest Engine → Валидация
2. Annual Cycle → "Что торговать"
3. Composite Line → "Когда входить"
4. Phenomenological → Проверка
5. COT/GBTC → "Умные деньги"
6. Risk Management → Позиция
7. QTB → Точка входа
8. Statistical Validation → p-value, CI
9. Data Lineage → Audit

---

## Y

### Year Digit
Последняя цифра года, используемая для Decennial Patterns.

**Диапазон:** 0-9

**Пример:** 2026 → year_digit = 6

---

## СОКРАЩЕНИЯ

| Сокращение | Полное название |
|------------|-----------------|
| AC | Annual Cycle |
| CI | Confidence Interval |
| COT | Commitment of Traders |
| CL | Composite Line |
| DTW | Dynamic Time Warping |
| FTE | Forward Testing Efficiency |
| GBTC | Grayscale Bitcoin Trust |
| MEM | Maximum Entropy Method |
| NAV | Net Asset Value |
| OHLCV | Open, High, Low, Close, Volume |
| PR | Percentile Rank |
| QTB | Qualified Trend Break |
| WFA | Walk-Forward Analysis |

---

**Версия документации:** 3.2 Final
