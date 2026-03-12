# AGENT_INSTRUCTIONS.md

> ⚠️ **ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ ПЕРЕД ЛЮБОЙ РАБОТОЙ**
> 
> Это НЕ рекомендация. Это ПРОТОКОЛ работы.

---

## 🤝 ПРАВИЛО #0: AGENT HANDSHAKE (ОБЯЗАТЕЛЬНО)

### Перед началом ЛЮБОЙ работы:

```
┌─────────────────────────────────────────────────────────────┐
│  ШАГ 1: ПРОВЕРИТЬ session.yaml                              │
│  → Есть ли активные сессии?                                 │
│  → Заблокирована ли задача?                                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ШАГ 2: ЗАРЕГИСТРИРОВАТЬСЯ                                   │
│  → python scripts/session_manager.py register <task_id>     │
│    "Agent Name" model                                       │
│  → Получить session_id                                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ШАГ 3: ПОДДЕРЖИВАТЬ HEARTBEAT                               │
│  → Каждые 30 минут обновлять heartbeat                      │
│  → python scripts/session_manager.py heartbeat <session_id> │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ШАГ 4: ЗАВЕРШИТЬ СЕССИЮ                                     │
│  → python scripts/session_manager.py complete <session_id>  │
│    success "Notes"                                          │
└─────────────────────────────────────────────────────────────┘
```

### Пример регистрации:

```bash
# 1. Проверить статус
python scripts/session_manager.py status

# 2. Зарегистрироваться
python scripts/session_manager.py register QS-001 "Claude (Anthropic)" claude-3-opus

# Вывод:
# {
#   "success": true,
#   "session_id": "session-abc12345",
#   "task_id": "QS-001",
#   "action": "you_can_start_working"
# }

# 3. Начать работу
python scripts/session_manager.py start session-abc12345

# 4. Heartbeat каждые 30 минут
python scripts/session_manager.py heartbeat session-abc12345

# 5. Завершить
python scripts/session_manager.py complete session-abc12345 success "QSpectrum prototype done"
```

### Если задача заблокирована:

```json
{
  "success": false,
  "error": "Task QS-001 is locked by GPT-4 (OpenAI)",
  "locked_by": "GPT-4 (OpenAI)",
  "session_id": "session-xyz789",
  "action": "choose_different_task"
}
```

**Действие:** Выбрать другую задачу из `tasks.yaml`.

---

## 🚨 КРИТИЧЕСКИЕ ПРАВИЛА

### Правило #1: Порядок чтения

```
1. session.yaml → проверить блокировки
2. progress.yaml → понять текущее состояние
3. tasks.yaml → взять следующую задачу
4. docs/TZ.md → понять требования
5. docs/PLAN.md → понять контекст
6. Выполнить задачу
7. ОБНОВЛИТЬ progress.yaml
8. ОБНОВЛИТЬ WORKLOG.md
9. ЗАВЕРШИТЬ СЕССИЮ в session.yaml
```

### Правило #2: Definition of Done

**ЗАПРЕЩЕНО** отмечать задачу как `completed: true` если:

- ❌ Не все пункты `definition_of_done` выполнены
- ❌ Тесты не проходят
- ❌ Код не соответствует `docs/CONVENTIONS.md`

### Правило #3: Блокеры

Если задача заблокирована:

```yaml
status: blocked
blocked_reason: "Конкретная причина"
```

**НЕ** пытаться выполнить заблокированную задачу.

### Правило #4: Валидация

Перед commit:

1. Запустить `make lint` — должно пройти без ошибок
2. Запустить `make test` — все тесты должны пройти
3. Проверить соответствие `docs/CONVENTIONS.md`

---

## 📋 ФОРМАТ ОБНОВЛЕНИЯ progress.yaml

При начале работы над задачей:

```yaml
current:
  active_task: QS-001

tasks:
  - id: QS-001
    status: in_progress
    assignee: "Claude"
    started: 2026-03-12T15:00:00Z
```

При завершении:

```yaml
tasks:
  - id: QS-001
    status: completed
    actual_hours: 6
    completed: 2026-03-12T21:00:00Z
```

---

## 🔍 АВТО-ПРОВЕРКИ (Self-Validation)

Перед завершением сессии агент ДОЛЖЕН проверить:

| Проверка | Команда | Ожидаемый результат |
|----------|---------|---------------------|
| Линтинг | `make lint` | 0 errors |
| Тесты | `make test` | All pass |
| Формат | `make format` | No changes |
| Типы | `make typecheck` | 0 errors |

---

## 🚫 ЗАПРЕЩЁННЫЕ ДЕЙСТВИЯ

1. ❌ **НЕ** удалять файлы без явного указания в задаче
2. ❌ **НЕ** менять `docs/TZ.md` без одобрения
3. ❌ **НЕ** пропускать этапы валидации
4. ❌ **НЕ** коммитить код с failing tests
5. ❌ **НЕ** игнорировать `definition_of_done`
6. ❌ **НЕ** работать над заблокированными задачами

---

## 📝 ШАБЛОН WORKLOG ЗАПИСИ

```markdown
---
**Task ID:** QS-001
**Agent:** Claude (Anthropic)
**Session:** session-002
**Date:** 2026-03-12 15:00 - 21:00
**Duration:** 6 hours

## Статус: ✅ COMPLETED

## Definition of Done Check
- [x] Файл quant/qspectrum/core.py создан
- [x] Функция cyclic_correlation() реализована
- [x] Функция burg_mem() реализована
- [x] Unit тесты проходят
- [x] Валидация на S&P 500 данных

## Что сделано
- Создан модуль quant/qspectrum/
- Реализован Burg's MEM алгоритм
- Добавлены unit тесты
- Проведена валидация

## Изменённые файлы
- `quant/qspectrum/core.py` - основной модуль
- `quant/qspectrum/burg.py` - MEM реализация
- `quant/tests/test_qspectrum.py` - тесты

## Метрики
- Lines of code: 450
- Test coverage: 85%
- Performance: O(n log n)

## Что делать дальше
1. QS-002: Bootstrap CI Streaming
2. PH-001: DTW Prototype

## Связь с документацией
- **TZ:** docs/TZ.md#3.2-qspectrum
- **PLAN:** docs/PLAN.md#phase-0
- **TECH:** docs/TECHNICAL_SOLUTION.md#4.1
```

---

## 🤝 ПЕРЕДАЧА МЕЖДУ АГЕНТАМИ

При передаче работы другому агенту:

1. Обновить `progress.yaml` с текущим состоянием
2. Добавить запись в `WORKLOG.md`
3. Указать `next_tasks` в `progress.yaml`
4. Оставить комментарий о незавершённых частях

---

## 📊 CHECKPOINT VALIDATION

Перед переходом на следующую фазу:

```yaml
# Автоматическая проверка checkpoint
phase_N_complete:
  criteria:
    - criterion: "..."
      status: true/false
  required_all: true  # Все criteria должны быть true
```

Если `required_all: false` → Go/No-Go решение принимает человек.

---

## 🔄 RECOVERY PROCEDURE

Если агент обнаружил проблему в предыдущей работе:

1. **НЕ** исправлять молча
2. Создать задачу-багрепорт в `tasks.yaml`:
   ```yaml
   - id: BUG-001
     type: bug
     severity: critical|high|medium|low
     description: "Описание проблемы"
     reported_by: "Agent Name"
     blocking: [list of blocked task IDs]
   ```
3. Продолжить работу над некритичными задачами

---

_Этот файл определяет протокол работы ИИ-агентов. Нарушение протокола = остановка разработки._
