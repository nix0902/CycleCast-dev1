# HANDSHAKE.md - Система регистрации ИИ-агентов

> **Версия:** 1.0.0 | **Создано:** 2026-03-12
>
> 🤝 **ОБЯЗАТЕЛЬНО:** Каждый агент ДОЛЖЕН зарегистрироваться перед работой.

---

## 🎯 Назначение

**Agent Handshake** обеспечивает:
- ✅ Регистрацию агента перед началом работы
- ✅ Блокировку задач от одновременного выполнения
- ✅ Отслеживание активных сессий
- ✅ Автоматический release при timeout
- ✅ Историю всех сессий

---

## 📋 ПРОТОКОЛ HANDSHAKE

### Шаг 1: Регистрация

Перед началом работы агент ДОЛЖЕН:

1. Прочитать `session.yaml` — проверить, не занята ли задача
2. Создать запись о сессии в `session.yaml`
3. Обновить `progress.yaml` с `active_task`
4. Начать работу

### Шаг 2: Завершение

После завершения:

1. Обновить статус в `session.yaml`
2. Обновить `progress.yaml`
3. Добавить запись в `WORKLOG.md`
4. Запустить `validate_progress.py`

---

## ⚡ ФОРМАТ session.yaml

```yaml
# session.yaml - Активные сессии агентов

meta:
  last_updated: "2026-03-12T16:00:00Z"
  protocol_version: "1.0.0"

# Текущие активные сессии
active_sessions: []

# История сессий
history:
  - session_id: "session-001"
    agent: "Claude (Anthropic)"
    model: "claude-3-opus"
    task_id: "DOC-001"
    status: "completed"
    registered: "2026-03-12T12:00:00Z"
    started: "2026-03-12T12:05:00Z"
    completed: "2026-03-12T14:30:00Z"
    duration_minutes: 145
    outcome: "success"
    next_task: "TEST-001"
```

---

## 🔒 ПРАВИЛА БЛОКИРОВКИ

### Правило #1: Одна задача — один агент

```yaml
# ЗАПРЕЩЕНО работать над задачей, если:
active_sessions:
  - task_id: "QS-001"  # ← Эта задача занята
    agent: "GPT-4"
    status: "in_progress"
```

### Правило #2: Timeout

```yaml
# Автоматический release через 2 часа неактивности
session:
  timeout_minutes: 120
  last_heartbeat: "2026-03-12T16:00:00Z"
```

### Правило #3: Heartbeat

Каждые 30 минут агент ДОЛЖЕН обновить `last_heartbeat`:

```yaml
active_sessions:
  - session_id: "session-003"
    task_id: "QS-001"
    last_heartbeat: "2026-03-12T16:30:00Z"  # ← Обновлять каждые 30 мин
```

---

## 🚨 КОНФЛИКТЫ

### Обнаружение конфликта

Если два агента пытаются взять одну задачу:

```yaml
conflict:
  detected: true
  task_id: "QS-001"
  agents:
    - "Claude (claimed at 12:00)"
    - "GPT-4 (claimed at 12:05)"
  resolution: "first_claim_wins"  # или "ask_human"
```

### Разрешение

1. Первый зарегистрировавшийся продолжает
2. Второй получает уведомление в `session.yaml`
3. Второй выбирает другую задачу

---

## 📊 СТАТУСЫ СЕССИЙ

| Статус | Описание |
|--------|----------|
| `registered` | Агент зарегистрировался, но не начал |
| `in_progress` | Агент работает |
| `paused` | Агент приостановил работу |
| `completed` | Задача завершена успешно |
| `failed` | Задача завершена с ошибкой |
| `timeout` | Сессия истекла по timeout |
| `conflict` | Обнаружен конфликт |

---

## 🔄 RECOVERY

### Автоматический release

Если `last_heartbeat` старше 2 часов:

```python
# Автоматически выполняется validate_progress.py
if now - last_heartbeat > 2 hours:
    session.status = "timeout"
    session.release_task()
    notify_agents()
```

### Ручной release

Если агент завершил работу некорректно:

```yaml
# Любой агент может освободить зависшую сессию
session:
  id: "session-003"
  status: "timeout"
  released_by: "Claude"
  released_at: "2026-03-12T18:00:00Z"
  reason: "No heartbeat for 3 hours"
```

---

## 📝 ШАБЛОН РЕГИСТРАЦИИ

При начале работы добавить в `session.yaml`:

```yaml
active_sessions:
  - session_id: "session-XXX"
    agent: "Claude (Anthropic)"
    model: "claude-3-opus"
    model_version: "20240229"
    task_id: "QS-001"
    status: "in_progress"
    registered: "2026-03-12T16:00:00Z"
    started: "2026-03-12T16:01:00Z"
    last_heartbeat: "2026-03-12T16:01:00Z"
    timeout_minutes: 120
    estimated_completion: "2026-03-12T22:00:00Z"
    contact_info: "session_id в WORKLOG.md"
```

---

## 🤝 ПЕРЕДАЧА МЕЖДУ АГЕНТАМИ

### Явная передача

```yaml
handover:
  from_agent: "Claude"
  to_agent: "GPT-4"
  task_id: "QS-001"
  reason: "Context limit reached"
  notes: "Burg's MEM done, need Bootstrap CI"
  transferred_at: "2026-03-12T18:00:00Z"
```

### Неявная (по timeout)

```yaml
handover:
  type: "timeout"
  from_agent: "Kimi"
  task_id: "QS-002"
  available_to: "any_agent"
  notes: "Session expired, partial work in WORKLOG #003"
```

---

_Этот файл определяет протокол Agent Handshake для координации работы._
