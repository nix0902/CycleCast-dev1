#!/usr/bin/env python3
"""
session_manager.py - Управление сессиями ИИ-агентов

Команды:
    python scripts/session_manager.py register <task_id> <agent_name>
    python scripts/session_manager.py heartbeat <session_id>
    python scripts/session_manager.py complete <session_id>
    python scripts/session_manager.py release <session_id>
    python scripts/session_manager.py status
    python scripts/session_manager.py validate
"""

import yaml
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import uuid


class SessionManager:
    """Управление сессиями ИИ-агентов с блокировками задач."""
    
    TIMEOUT_MINUTES = 120
    HEARTBEAT_INTERVAL = 30
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
        self.session_file = project_root / "session.yaml"
        self.tasks_file = project_root / "tasks.yaml"
        self.progress_file = project_root / "progress.yaml"
        
    def load_yaml(self, path: Path) -> dict:
        """Загрузка YAML файла."""
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def save_yaml(self, path: Path, data: dict):
        """Сохранение YAML файла."""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def get_timestamp(self) -> str:
        """Получение текущего timestamp в ISO формате."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def generate_session_id(self) -> str:
        """Генерация уникального ID сессии."""
        return f"session-{uuid.uuid4().hex[:8]}"
    
    # ==========================================
    # КОМАНДЫ
    # ==========================================
    
    def register(self, task_id: str, agent_name: str, model: str = "unknown") -> dict:
        """
        Регистрация новой сессии агента.
        
        Args:
            task_id: ID задачи из tasks.yaml
            agent_name: Имя агента (напр. "Claude (Anthropic)")
            model: Модель агента (напр. "claude-3-opus")
            
        Returns:
            dict с session_id и статусом
        """
        session_data = self.load_yaml(self.session_file)
        tasks_data = self.load_yaml(self.tasks_file)
        
        # Проверка: существует ли задача?
        task_exists = False
        for task in tasks_data.get('tasks', []):
            if task.get('id') == task_id:
                task_exists = True
                break
        
        if not task_exists:
            return {
                "success": False,
                "error": f"Task {task_id} not found in tasks.yaml",
                "action": "check_tasks_yaml"
            }
        
        # Проверка: не заблокирована ли задача другим агентом?
        for active in session_data.get('active_sessions', []):
            if active.get('task_id') == task_id:
                return {
                    "success": False,
                    "error": f"Task {task_id} is locked by {active.get('agent')}",
                    "locked_by": active.get('agent'),
                    "session_id": active.get('session_id'),
                    "action": "choose_different_task"
                }
        
        # Проверка: не заблокирована ли задача зависимостями?
        blocked = session_data.get('blocked_tasks', {})
        if task_id in blocked:
            return {
                "success": False,
                "error": f"Task {task_id} is blocked: {blocked[task_id].get('reason')}",
                "blocked_by": blocked[task_id].get('blocked_by', []),
                "action": "complete_dependencies_first"
            }
        
        # Создание новой сессии
        session_id = self.generate_session_id()
        now = self.get_timestamp()
        
        new_session = {
            "session_id": session_id,
            "agent": agent_name,
            "model": model,
            "task_id": task_id,
            "status": "registered",
            "registered": now,
            "started": None,
            "last_heartbeat": now,
            "timeout_minutes": self.TIMEOUT_MINUTES,
            "estimated_completion": None,
            "notes": None
        }
        
        # Добавление в active_sessions
        if 'active_sessions' not in session_data:
            session_data['active_sessions'] = []
        session_data['active_sessions'].append(new_session)
        
        # Обновление блокировки задачи
        if 'task_locks' not in session_data:
            session_data['task_locks'] = {}
        session_data['task_locks'][task_id] = {
            "locked": True,
            "locked_by": agent_name,
            "locked_at": now,
            "session_id": session_id
        }
        
        # Обновление meta
        session_data['meta'] = session_data.get('meta', {})
        session_data['meta']['last_updated'] = now
        
        self.save_yaml(self.session_file, session_data)
        
        return {
            "success": True,
            "session_id": session_id,
            "task_id": task_id,
            "agent": agent_name,
            "registered": now,
            "action": "you_can_start_working",
            "reminder": f"Update heartbeat every {self.HEARTBEAT_INTERVAL} minutes"
        }
    
    def start(self, session_id: str) -> dict:
        """Подтверждение начала работы (после регистрации)."""
        session_data = self.load_yaml(self.session_file)
        now = self.get_timestamp()
        
        for session in session_data.get('active_sessions', []):
            if session.get('session_id') == session_id:
                session['status'] = 'in_progress'
                session['started'] = now
                session['last_heartbeat'] = now
                session_data['meta']['last_updated'] = now
                self.save_yaml(self.session_file, session_data)
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "in_progress",
                    "started": now
                }
        
        return {
            "success": False,
            "error": f"Session {session_id} not found"
        }
    
    def heartbeat(self, session_id: str) -> dict:
        """Обновление heartbeat (агент активен)."""
        session_data = self.load_yaml(self.session_file)
        now = self.get_timestamp()
        
        for session in session_data.get('active_sessions', []):
            if session.get('session_id') == session_id:
                session['last_heartbeat'] = now
                session_data['meta']['last_updated'] = now
                self.save_yaml(self.session_file, session_data)
                return {
                    "success": True,
                    "session_id": session_id,
                    "last_heartbeat": now,
                    "timeout_at": self._get_timeout_time(now)
                }
        
        return {
            "success": False,
            "error": f"Session {session_id} not found"
        }
    
    def complete(self, session_id: str, outcome: str = "success", notes: str = None) -> dict:
        """Завершение сессии."""
        session_data = self.load_yaml(self.session_file)
        now = self.get_timestamp()
        
        session_to_complete = None
        session_index = None
        
        for i, session in enumerate(session_data.get('active_sessions', [])):
            if session.get('session_id') == session_id:
                session_to_complete = session
                session_index = i
                break
        
        if not session_to_complete:
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }
        
        # Вычисление duration
        started = session_to_complete.get('started')
        if started:
            start_time = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
            end_time = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
        else:
            duration_minutes = 0
        
        # Обновление сессии
        session_to_complete['status'] = 'completed'
        session_to_complete['completed'] = now
        session_to_complete['duration_minutes'] = duration_minutes
        session_to_complete['outcome'] = outcome
        session_to_complete['notes'] = notes
        
        # Перемещение в history
        if 'history' not in session_data:
            session_data['history'] = []
        session_data['history'].append(session_to_complete)
        
        # Удаление из active_sessions
        session_data['active_sessions'].pop(session_index)
        
        # Освобождение блокировки задачи
        task_id = session_to_complete.get('task_id')
        if task_id and task_id in session_data.get('task_locks', {}):
            session_data['task_locks'][task_id] = {"locked": False}
        
        session_data['meta']['last_updated'] = now
        self.save_yaml(self.session_file, session_data)
        
        return {
            "success": True,
            "session_id": session_id,
            "task_id": task_id,
            "status": "completed",
            "outcome": outcome,
            "duration_minutes": duration_minutes,
            "action": "update_worklog_and_progress"
        }
    
    def release(self, session_id: str, reason: str = "manual_release") -> dict:
        """Принудительное освобождение сессии (например, по timeout)."""
        session_data = self.load_yaml(self.session_file)
        now = self.get_timestamp()
        
        for i, session in enumerate(session_data.get('active_sessions', [])):
            if session.get('session_id') == session_id:
                session['status'] = 'released'
                session['released_at'] = now
                session['release_reason'] = reason
                
                # Перемещение в history
                if 'history' not in session_data:
                    session_data['history'] = []
                session_data['history'].append(session)
                
                # Удаление из active_sessions
                session_data['active_sessions'].pop(i)
                
                # Освобождение блокировки
                task_id = session.get('task_id')
                if task_id and task_id in session_data.get('task_locks', {}):
                    session_data['task_locks'][task_id] = {"locked": False}
                
                session_data['meta']['last_updated'] = now
                self.save_yaml(self.session_file, session_data)
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "task_id": task_id,
                    "status": "released",
                    "reason": reason,
                    "action": "task_is_now_available"
                }
        
        return {
            "success": False,
            "error": f"Session {session_id} not found"
        }
    
    def status(self) -> dict:
        """Получение статуса всех сессий."""
        session_data = self.load_yaml(self.session_file)
        tasks_data = self.load_yaml(self.tasks_file)
        
        active = session_data.get('active_sessions', [])
        
        # Проверка timeout
        now = datetime.utcnow()
        timed_out = []
        for session in active:
            last_heartbeat = session.get('last_heartbeat')
            if last_heartbeat:
                heartbeat_time = datetime.strptime(last_heartbeat, "%Y-%m-%dT%H:%M:%SZ")
                if (now - heartbeat_time).total_seconds() > self.TIMEOUT_MINUTES * 60:
                    timed_out.append(session.get('session_id'))
        
        return {
            "active_sessions": len(active),
            "sessions": active,
            "timed_out_sessions": timed_out,
            "available_tasks": self._get_available_tasks(session_data, tasks_data),
            "blocked_tasks": list(session_data.get('blocked_tasks', {}).keys()),
            "meta": session_data.get('meta', {})
        }
    
    def validate(self) -> dict:
        """Валидация состояния сессий и автоматический release timeout."""
        session_data = self.load_yaml(self.session_file)
        now = datetime.utcnow()
        
        errors = []
        warnings = []
        released = []
        
        # Проверка timeout
        active = session_data.get('active_sessions', [])
        sessions_to_release = []
        
        for session in active:
            last_heartbeat = session.get('last_heartbeat')
            if last_heartbeat:
                heartbeat_time = datetime.strptime(last_heartbeat, "%Y-%m-%dT%H:%M:%SZ")
                minutes_since_heartbeat = (now - heartbeat_time).total_seconds() / 60
                
                if minutes_since_heartbeat > self.TIMEOUT_MINUTES:
                    sessions_to_release.append({
                        "session_id": session.get('session_id'),
                        "task_id": session.get('task_id'),
                        "agent": session.get('agent'),
                        "minutes_inactive": int(minutes_since_heartbeat)
                    })
        
        # Автоматический release
        for session_info in sessions_to_release:
            result = self.release(
                session_info['session_id'],
                f"Timeout: no heartbeat for {session_info['minutes_inactive']} minutes"
            )
            if result.get('success'):
                released.append(session_info)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "auto_released": released,
            "total_active_sessions": len(active) - len(released)
        }
    
    # ==========================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================
    
    def _get_timeout_time(self, last_heartbeat: str) -> str:
        """Вычисление времени timeout."""
        heartbeat_time = datetime.strptime(last_heartbeat, "%Y-%m-%dT%H:%M:%SZ")
        timeout_time = heartbeat_time + timedelta(minutes=self.TIMEOUT_MINUTES)
        return timeout_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def _get_available_tasks(self, session_data: dict, tasks_data: dict) -> List[str]:
        """Получение списка доступных (не заблокированных) задач."""
        locked_tasks = set()
        for task_id, lock in session_data.get('task_locks', {}).items():
            if lock.get('locked'):
                locked_tasks.add(task_id)
        
        blocked_tasks = set(session_data.get('blocked_tasks', {}).keys())
        
        available = []
        for task in tasks_data.get('tasks', []):
            task_id = task.get('id')
            if task_id not in locked_tasks and task_id not in blocked_tasks:
                if task.get('status') == 'pending':
                    available.append(task_id)
        
        return available


def print_help():
    """Вывод справки."""
    print("""
🤝 Session Manager - Управление сессиями ИИ-агентов

Команды:

  register <task_id> <agent_name> [model]
    Регистрация новой сессии для задачи
    
  start <session_id>
    Подтверждение начала работы
    
  heartbeat <session_id>
    Обновление heartbeat (агент активен)
    
  complete <session_id> [outcome] [notes]
    Завершение сессии
    
  release <session_id> [reason]
    Принудительное освобождение сессии
    
  status
    Статус всех сессий
    
  validate
    Валидация и авто-release timeout сессий

Примеры:

  python scripts/session_manager.py register QS-001 "Claude (Anthropic)" claude-3-opus
  python scripts/session_manager.py start session-abc12345
  python scripts/session_manager.py heartbeat session-abc12345
  python scripts/session_manager.py complete session-abc12345 success "Done"
  python scripts/session_manager.py status
  python scripts/session_manager.py validate
""")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = SessionManager()
    
    if command == "register":
        if len(sys.argv) < 4:
            print("❌ Usage: register <task_id> <agent_name> [model]")
            sys.exit(1)
        task_id = sys.argv[2]
        agent_name = sys.argv[3]
        model = sys.argv[4] if len(sys.argv) > 4 else "unknown"
        result = manager.register(task_id, agent_name, model)
        
    elif command == "start":
        if len(sys.argv) < 3:
            print("❌ Usage: start <session_id>")
            sys.exit(1)
        result = manager.start(sys.argv[2])
        
    elif command == "heartbeat":
        if len(sys.argv) < 3:
            print("❌ Usage: heartbeat <session_id>")
            sys.exit(1)
        result = manager.heartbeat(sys.argv[2])
        
    elif command == "complete":
        if len(sys.argv) < 3:
            print("❌ Usage: complete <session_id> [outcome] [notes]")
            sys.exit(1)
        session_id = sys.argv[2]
        outcome = sys.argv[3] if len(sys.argv) > 3 else "success"
        notes = sys.argv[4] if len(sys.argv) > 4 else None
        result = manager.complete(session_id, outcome, notes)
        
    elif command == "release":
        if len(sys.argv) < 3:
            print("❌ Usage: release <session_id> [reason]")
            sys.exit(1)
        session_id = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else "manual_release"
        result = manager.release(session_id, reason)
        
    elif command == "status":
        result = manager.status()
        
    elif command == "validate":
        result = manager.validate()
        
    elif command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)
        
    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        sys.exit(1)
    
    # Вывод результата
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
