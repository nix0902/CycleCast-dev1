# ДЕТАЛЬНЫЙ ПЛАН РАЗРАБОТКИ
## Система циклического анализа и прогнозирования финансовых рынков
### CycleCast v3.2 Final - Методология Ларри Вильямса

---

## 1. ОБЗОР ПРОЕКТА

| Параметр | Значение |
|----------|----------|
| Название | CycleCast v3.2 Final |
| Длительность | 44 недели (~11 месяцев) |
| Команда | 6-7 человек |
| Стек | Go, Python, PostgreSQL, TimescaleDB, Redis, React |

---

## 2. ФАЗЫ РАЗРАБОТКИ

### Phase 0: Backtesting & Math Prototyping (Недели 1-4) **КРИТИЧЕСКИЙ**
| Неделя | Задача | Результат | Go/No-Go Критерий |
|--------|--------|-----------|-------------------|
| 1.1 | Python-прототип QSpectrum | Jupyter Notebook с Burg's MEM | < 3 сек на 10 лет |
| 1.2 | Python-прототип DTW (гибрид) | Валидация Phenomenological | < 3 сек на 10 лет |
| 1.3 | Robust Normalization | Percentile Rank тест | — |
| 2.1 | Backtest Engine (Go) | Симуляция на истории | — |
| 2.2 | Учёт комиссий/проскальзывания | Реалистичные метрики | — |
| 3.1 | In-Sample / Out-of-Sample | Разделение данных | — |
| 3.2 | Метрики (Sharpe, MaxDD) | Отчёт по стратегии | — |
| 3.3 | Bootstrap CI (streaming) | 1000 итераций | — |
| 4.1 | Валидация на BTC/GBTC | Тест 2020-2025 | — |
| 4.2 | Chow Test + Regime Detection | Структурный сдвиг | — |
| **4.3** | **Go/No-Go Decision** | **Решение о продолжении** | **Sharpe > 1.0, FTE > 0.08, GBTC > 0.5, CI > 0** |

**Критерий завершения:** Equity curve > 0 на out-of-sample данных, p-value < 0.05

---

### Phase 1: Фундамент (Недели 5-8)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 5.1 | Go проект, структура | go.mod, директории |
| 5.2 | Docker Compose | PostgreSQL, Redis, API |
| 6.1 | Схема БД + миграции | Таблицы, индексы |
| 6.2 | Repository layer | CRUD операции |
| 7.1 | Market Data Service | Импорт, API провайдеры |
| 7.2 | Circuit Breaker | Graceful degradation |
| 8.1 | API Gateway (Gin) | Роутинг, middleware |
| 8.2 | Swagger/OpenAPI | Документация |

---

### Phase 2: Annual Cycle & Seasonality (Недели 9-11)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 9.1 | Загрузка 30-50 лет данных | Исторические OHLC |
| 9.2 | Детрендинг + нормализация | Сезонная кривая |
| 10.1 | FTE валидация | Корреляция прогноз/факт |
| 10.2 | Адаптивный порог | Regime detection |
| 11.1 | Seasonality Dashboard | Визуализация (React) |

---

### Phase 3: QSpectrum & Composite Line (Недели 12-15)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 12.1 | Python gRPC сервис | Интеграция Go ↔ Python |
| 12.2 | Циклическая корреляция | Спектр циклов |
| 13.1 | Burg's MEM (Python) | Спектральная плотность |
| 13.2 | WFA устойчивости | Валидация циклов |
| 14.1 | Composite Line Generator | 3 волны, резонанс |
| 14.2 | U-Turn Detection | Точки разворота |
| 15.1 | API endpoints | /analysis/qspectrum, /composite |

---

### Phase 4: Decennial Patterns (Недели 16-18)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 16.1 | Группировка по yearDigit | Паттерны 0-9 |
| 16.2 | Нормализация | Масштаб 0-1 |
| 17.1 | Корреляция с текущим годом | Similarity Score |
| 17.2 | API endpoints | /analysis/decennial |
| 18.1 | Отключение для crypto | < 30 лет данных |

---

### Phase 5: Phenomenological Model (Недели 19-21)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 19.1 | DTW гибридный (Python) | Поиск аналогий |
| 19.2 | Фильтр по Decennial | yearDigit фильтр |
| 20.1 | Best Matches Ranking | Топ совпадений |
| 20.2 | Проекция продолжения | Прогноз |
| 21.1 | API endpoints | /analysis/phenom |

---

### Phase 6: COT/GBTC Analysis (Недели 22-25)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 22.1 | Парсер CFTC COT | Импорт отчётов |
| 22.2 | Парсер GBTC/ETF | Grayscale API, Yahoo |
| 23.1 | Миграция БД | Новые поля |
| 23.2 | analyzeTrustPremium | Логика GBTC Index |
| 23.3 | regime_change_date | Учёт ETF конвертации |
| 23.4 | signal_direction (-1) | Инверсия сигнала |
| 24.1 | Percentile Rank | Устойчивость к выбросам |
| 24.2 | Autocorrelation Filter | Фильтрация кластеров |
| 24.3 | Liquidity-Weighted | GBTC + IBIT + FBTC |
| 25.1 | Тестирование 2020-2025 | Backtest GBTC proxy |

---

### Phase 7: Risk Management (Недели 26-27)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 26.1 | Position Sizing | Расчёт размера |
| 26.2 | Stop-Loss / Take-Profit | Уровни выхода |
| 27.1 | Max Drawdown лимит | Защита капитала |
| 27.2 | Signal Decay Function | Затухание сигнала |

---

### Phase 8: Qualified Trend Break (Недели 28-29)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 28.1 | Детекция пробоев | Трендовые линии |
| 28.2 | Фильтрация Composite | Confirm / False |
| 29.1 | API endpoints | /analysis/qtb |

---

### Phase 9: Integration & Workflow (Недели 30-32)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 30.1 | Объединение всех модулей | Единый workflow |
| 30.2 | Автоматический выбор активов | Seasonality + FTE |
| 31.1 | Генерация сигналов | Composite + COT + Phenom |
| 31.2 | Risk интеграция | Позиция на сигнал |
| 31.3 | Statistical Validation | p-value, CI |
| 32.1 | Paper Trading режим | Демо-счета |

---

### Phase 10: ML, Monitoring & Compliance (Недели 33-44)
| Неделя | Задача | Результат |
|--------|--------|-----------|
| 33.1 | Feature Engineering | Сигналы → features |
| 33.2 | Label Generation | logging only |
| 34.1 | XGBoost Classifier | Модель обучена |
| 34.2 | Cross-Validation | OOS тестирование |
| 35.1 | Monitoring Stack | Prometheus + Grafana |
| 35.2 | Alerting Rules | 6 критических алертов |
| 36.1 | Chaos Tests | 5 сценариев fault injection |
| **36.2** | **Data Lineage System** | **Audit trail** |
| **37.1** | **Audit Logging** | **Compliance** |
| **37.2** | **Compliance Reporting** | **SEC/CFTC ready** |
| 38-40 | Frontend (React) | Dashboard, графики |
| 41.1 | Unit тесты | Покрытие > 80% |
| 41.2 | Integration тесты | API тесты |
| 42.1 | Load testing | k6, оптимизация |
| **42.2** | **Security Audit** | **Penetration test** |
| 43.1 | Documentation | Godoc, API docs |
| 44.1 | Production Deployment | Kubernetes |
| 44.2 | Final Acceptance | Sign-off |

---

## 3. КОМАНДА И РОЛИ

| Роль | Количество | Обязанности |
|------|------------|-------------|
| Tech Lead / Architect | 1 | Архитектура, код-ревью, Go/Python |
| Backend Developer (Go) | 2 | API, сервисы, БД |
| Quant Developer (Python) | 1 | QSpectrum, DTW, Bootstrap |
| ML Engineer | 1 | XGBoost, Monitoring (Phase 10) |
| Frontend Developer | 1 | React, графики |
| DevOps | 1 | CI/CD, инфраструктура, Vault |
| QA | 1 | Тестирование, бэктест валидация |

---

## 4. КЛЮЧЕВЫЕ МЕТРИКИ

### 4.1 Производительность
| Метрика | Цель |
|---------|------|
| API Response Time | < 100ms (p95) |
| Python gRPC call | < 500ms |
| Annual Cycle расчёт | < 200ms |
| Composite Line | < 100ms |
| WebSocket latency | < 10ms |

### 4.2 Надёжность
| Метрика | Цель |
|---------|------|
| Uptime | 99.9% |
| Error rate | < 0.1% |
| Data integrity | 100% |

### 4.3 Trading Quality
| Метрика | Цель |
|---------|------|
| Backtest Sharpe | > 1.0 |
| Max Drawdown | < 20% |
| Win Rate | > 50% |
| Out-of-Sample Correlation | > 0.08 (Crypto), > 0.0 (TradFi) |
| p-value | < 0.05 |
| Bootstrap CI (95%) | Положительный return |

---

## 5. РИСКИ И МИТИГАЦИЯ

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Сложность математики (Burg's MEM) | Высокая | Высокое | Python-прототип до Go-кода |
| Неточность прогнозов | Средняя | Высокое | FTE, WFA, Backtest валидация |
| Качество данных (30-50 лет) | Средняя | Высокое | Множественные источники, валидация |
| GBTC структурный слом (2024) | Высокая | Среднее | regime_change_date + Chow Test |
| Производительность DTW | Средняя | Среднее | Гибридный алгоритм, кэширование |
| Переобучение стратегии | Средняя | Высокое | In-Sample / Out-of-Sample разделение |
| Bootstrap вычислительно тяжёл | Средняя | Среднее | Только Python, streaming, кэширование |
| Autocorrelation сигналов | Средняя | Среднее | min_signal_distance_days = 21 |
| Quant Developer bottleneck | Высокая | Высокое | Найм до старта Phase 0 |

---

## 6. ИТОГОВАЯ ОЦЕНКА

| Этап | Длительность |
|------|--------------|
| Phase 0: Backtest & Math | 4 недели |
| Phase 1: Фундамент | 4 недели |
| Phase 2: Annual Cycle | 3 недели |
| Phase 3: QSpectrum & Composite | 4 недели |
| Phase 4: Decennial | 3 недели |
| Phase 5: Phenomenological | 3 недели |
| Phase 6: COT/GBTC | 4 недели |
| Phase 7: Risk Management | 2 недели |
| Phase 8: QTB | 2 недели |
| Phase 9: Integration | 3 недели |
| Phase 10: ML, Monitoring, Compliance | 12 недель |
| **ИТОГО** | **44 недели (~11 месяцев)** |

---

## 7. ЧЕК-ЛИСТ ПЕРЕД СТАРТОМ (SPRINT 1)

### Blocking (без этого — СТОП):
- [ ] **Quant Developer (senior)** — контракт подписан, start date < Неделя 1
- [ ] **Данные:** 30 лет TradFi (verified), 15 лет BTC (verified) — **no gaps > 5 days**
- [ ] **Python-прототип:** Burg's MEM + DTW гибрид — **< 3 сек на 10 лет**
- [ ] **Vault:** secrets injection — **tested, rotation working**
- [ ] **Go/No-Go критерии:** **signed off by stakeholders + legal**

### Critical (риск задержки):
- [ ] **Circuit Breaker** — implemented, **tested with fault injection**
- [ ] **Continuous Aggregates** — **performance benchmarked (query < 50ms)**
- [ ] **gRPC Streaming** — **only Bootstrap, tested with 10K iterations**

### High (качество):
- [ ] **Monitoring Stack** — **deployed, dashboards reviewed**
- [ ] **Alerting Rules** — **6 alerts, 2 critical with PagerDuty**
- [ ] **Chaos Test Plan** — **5 сценариев включая network partition**
- [ ] **Data Lineage Design** — **approved (Phase 10)**

---

## 8. ЗАКЛЮЧИТЕЛЬНОЕ СЛОВО

**CycleCast v3.2 Final** — это production-ready система институционального уровня для циклического анализа рынков с учётом:
- ✅ Традиционных активов (30-50 лет данных, COT)
- ✅ Криптовалют (10-15 лет, GBTC/ETF proxy)
- ✅ Backtesting Engine до продакшена
- ✅ Risk Management для защиты капитала
- ✅ Python для сложной математики (Burg's MEM, DTW, Bootstrap)
- ✅ Go для высокопроизводительного ядра
- ✅ Статистическая значимость (p-value, CI)
- ✅ Robust нормализация (Percentile Rank)
- ✅ Autocorrelation Filter (min 21 день)
- ✅ Liquidity-Weighted Aggregation
- ✅ Signal Decay Function
- ✅ Chow Test для структурных сдвигов
- ✅ Data Lineage для compliance
- ✅ Monitoring & Alerting
- ✅ Chaos Engineering tests
- ✅ Circuit Breaker pattern

**Зелёный свет.** Приступайте к **Phase 0**.

---

**Дата утверждения:** 12 марта 2026  
**Версия документации:** 3.2 Final  
**Статус:** ✅ **УТВЕРЖДЕНО К РАЗРАБОТКЕ**
