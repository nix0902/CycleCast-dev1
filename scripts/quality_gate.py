#!/usr/bin/env python3
"""
quality_gate.py - Система проверки качества (Quality Gate)

Команды:
    python scripts/quality_gate.py submit <task_id>
    python scripts/quality_gate.py take-review
    python scripts/quality_gate.py approve <task_id> --rating 5
    python scripts/quality_gate.py reject <task_id> --reason "Tests failing"
    python scripts/quality_gate.py status
    python scripts/quality_gate.py history <agent_name>
"""

import yaml
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any


class QualityGate:
    """Система проверки качества: второй агент проверяет работу первого."""
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
        self.quality_file = project_root / "quality_gate.yaml"
        self.tasks_file = project_root / "tasks.yaml"
        self.skills_file = project_root / "agent_skills.yaml"
        self.session_file = project_root / "session.yaml"
        self.worklog_file = project_root / "WORKLOG.md"
        
        # Загрузка данных
        self.quality_data = self._load_yaml(self.quality_file)
        self.tasks_data = self._load_yaml(self.tasks_file)
        self.skills_data = self._load_yaml(self.skills_file)
        self.session_data = self._load_yaml(self.session_file)
    
    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _save_yaml(self, path: Path, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _get_timestamp(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # ==========================================
    # SUBMIT FOR REVIEW
    # ==========================================
    
    def submit_for_review(self, task_id: str, worker_agent: str = None) -> dict:
        """
        Отправить завершённую задачу на review.
        """
        # Найти задачу
        task = None
        for t in self.tasks_data.get('tasks', []):
            if t.get('id') == task_id:
                task = t
                break
        
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Проверить статус
        if task.get('status') not in ['in_progress', 'pending_review']:
            return {
                "success": False,
                "error": f"Task status must be 'in_progress' or 'pending_review', got '{task.get('status')}'"
            }
        
        # Получить автора
        if not worker_agent:
            worker_agent = task.get('assignee', 'Unknown Agent')
        
        # Создать review request
        review_request = {
            'task_id': task_id,
            'submitted_by': worker_agent,
            'submitted_at': self._get_timestamp(),
            'priority': task.get('priority', 'normal'),
            'review_deadline': None,  # TODO: calculate
            'auto_assign_to': self._find_reviewer(worker_agent, task),
            'dod_checklist': task.get('definition_of_done', []),
            'files_changed': []  # TODO: detect from git
        }
        
        # Добавить в pending_reviews
        if 'pending_reviews' not in self.quality_data:
            self.quality_data['pending_reviews'] = []
        self.quality_data['pending_reviews'].append(review_request)
        
        # Обновить статус задачи
        task['status'] = 'pending_review'
        task['review_requested_at'] = self._get_timestamp()
        
        # Сохранить
        self._save_yaml(self.quality_file, self.quality_data)
        self._save_yaml(self.tasks_file, self.tasks_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "pending_review",
            "suggested_reviewer": review_request.get('auto_assign_to'),
            "action": "wait_for_reviewer"
        }
    
    def _find_reviewer(self, worker_agent: str, task: dict) -> Optional[str]:
        """
        Найти подходящего ревьюера (не автора).
        """
        reviewers = self.quality_data.get('reviewers', {})
        task_type = task.get('task_type', '')
        
        # Отфильтровать доступных ревьюеров
        available = []
        for name, data in reviewers.items():
            # Пропустить автора
            if worker_agent and worker_agent in name:
                continue
            
            if not data.get('available', True):
                continue
            
            # Проверить специализации
            specs = data.get('specializations', [])
            score = data.get('success_rate_as_reviewer', 0.5)
            
            # Бонус за соответствующую специализацию
            if any(s in specs for s in ['code-review', 'qa', 'testing']):
                score += 0.1
            
            available.append((name, score))
        
        # Сортировать по score
        available.sort(key=lambda x: x[1], reverse=True)
        
        return available[0][0] if available else None
    
    # ==========================================
    # TAKE REVIEW
    # ==========================================
    
    def take_review(self, reviewer_agent: str = None) -> dict:
        """
        Взять следующую задачу на review.
        """
        pending = self.quality_data.get('pending_reviews', [])
        
        if not pending:
            return {
                "success": False,
                "error": "No tasks pending review",
                "action": "wait_for_submissions"
            }
        
        # Выбрать задачу (FIFO или по приоритету)
        # Сортируем по приоритету
        priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
        pending.sort(key=lambda x: priority_order.get(x.get('priority', 'normal'), 2))
        
        review = pending[0]
        
        # Проверить конфликт
        worker = review.get('submitted_by', '')
        if reviewer_agent and reviewer_agent in worker:
            # Конфликт - ищем другую задачу
            for r in pending[1:]:
                if reviewer_agent not in r.get('submitted_by', ''):
                    review = r
                    break
            else:
                return {
                    "success": False,
                    "error": f"All pending reviews submitted by {reviewer_agent}",
                    "conflict": "cannot_review_own_work"
                }
        
        # Переместить в active_reviews
        pending.remove(review)
        
        active_review = {
            'task_id': review['task_id'],
            'reviewer': reviewer_agent,
            'started_at': self._get_timestamp(),
            'status': 'in_progress',
            'deadline': None,
            'worker': review.get('submitted_by'),
            'checklist': review.get('dod_checklist', [])
        }
        
        if 'active_reviews' not in self.quality_data:
            self.quality_data['active_reviews'] = []
        self.quality_data['active_reviews'].append(active_review)
        
        self._save_yaml(self.quality_file, self.quality_data)
        
        return {
            "success": True,
            "task_id": review['task_id'],
            "reviewer": reviewer_agent,
            "worker": review.get('submitted_by'),
            "checklist": review.get('dod_checklist', []),
            "action": "perform_review",
            "commands": {
                "approve": f"python scripts/quality_gate.py approve {review['task_id']} --rating 5",
                "reject": f"python scripts/quality_gate.py reject {review['task_id']} --reason '...'"
            }
        }
    
    # ==========================================
    # APPROVE / REJECT
    # ==========================================
    
    def approve(self, task_id: str, reviewer: str, rating: int = 5, comments: List[str] = None) -> dict:
        """
        Одобрить задачу после review.
        """
        # Найти active review
        active = None
        for r in self.quality_data.get('active_reviews', []):
            if r.get('task_id') == task_id:
                active = r
                break
        
        if not active:
            return {"success": False, "error": f"No active review for task {task_id}"}
        
        # Вычислить время review
        started = active.get('started_at', '')
        review_time = 0
        if started:
            try:
                start_time = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
                end_time = datetime.utcnow()
                review_time = int((end_time - start_time).total_seconds() / 60)
            except:
                pass
        
        # Создать результат
        result = {
            'task_id': task_id,
            'worker': active.get('worker'),
            'reviewer': reviewer,
            'result': 'approved',
            'reviewed_at': self._get_timestamp(),
            'review_time_minutes': review_time,
            'rating': rating,
            'comments': comments or []
        }
        
        # Переместить в history
        self.quality_data['active_reviews'].remove(active)
        if 'review_history' not in self.quality_data:
            self.quality_data['review_history'] = []
        self.quality_data['review_history'].append(result)
        
        if 'review_results' not in self.quality_data:
            self.quality_data['review_results'] = []
        self.quality_data['review_results'].append(result)
        
        # Обновить статус задачи
        for task in self.tasks_data.get('tasks', []):
            if task.get('id') == task_id:
                task['status'] = 'completed'
                task['reviewed_at'] = self._get_timestamp()
                task['reviewer'] = reviewer
                task['review_rating'] = rating
                break
        
        # Обновить статистику
        self._update_stats(result)
        
        self._save_yaml(self.quality_file, self.quality_data)
        self._save_yaml(self.tasks_file, self.tasks_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "result": "approved",
            "rating": rating,
            "review_time_minutes": review_time,
            "action": "task_completed"
        }
    
    def reject(self, task_id: str, reviewer: str, reason: str, issues: List[dict] = None) -> dict:
        """
        Отклонить задачу с комментариями для доработки.
        """
        # Найти active review
        active = None
        for r in self.quality_data.get('active_reviews', []):
            if r.get('task_id') == task_id:
                active = r
                break
        
        if not active:
            return {"success": False, "error": f"No active review for task {task_id}"}
        
        # Вычислить время review
        started = active.get('started_at', '')
        review_time = 0
        if started:
            try:
                start_time = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
                end_time = datetime.utcnow()
                review_time = int((end_time - start_time).total_seconds() / 60)
            except:
                pass
        
        # Создать результат
        result = {
            'task_id': task_id,
            'worker': active.get('worker'),
            'reviewer': reviewer,
            'result': 'rejected',
            'reviewed_at': self._get_timestamp(),
            'review_time_minutes': review_time,
            'reason': reason,
            'issues': issues or [],
            'rework_cycle': 1  # TODO: track cycles
        }
        
        # Переместить в history
        self.quality_data['active_reviews'].remove(active)
        if 'review_history' not in self.quality_data:
            self.quality_data['review_history'] = []
        self.quality_data['review_history'].append(result)
        
        if 'review_results' not in self.quality_data:
            self.quality_data['review_results'] = []
        self.quality_data['review_results'].append(result)
        
        # Обновить статус задачи
        for task in self.tasks_data.get('tasks', []):
            if task.get('id') == task_id:
                task['status'] = 'rework'
                task['reviewed_at'] = self._get_timestamp()
                task['reviewer'] = reviewer
                task['rework_reason'] = reason
                task['rework_issues'] = issues
                break
        
        # Обновить статистику
        self._update_stats(result)
        
        self._save_yaml(self.quality_file, self.quality_data)
        self._save_yaml(self.tasks_file, self.tasks_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "result": "rejected",
            "status": "rework",
            "reason": reason,
            "issues": issues,
            "action": "worker_must_fix_issues"
        }
    
    def _update_stats(self, result: dict):
        """Обновление статистики."""
        stats = self.quality_data.get('statistics', {})
        
        stats['total_reviews'] = stats.get('total_reviews', 0) + 1
        
        if result.get('result') == 'approved':
            stats['approved'] = stats.get('approved', 0) + 1
        else:
            stats['rejected'] = stats.get('rejected', 0) + 1
        
        total = stats['total_reviews']
        stats['approval_rate'] = stats['approved'] / total if total > 0 else 0
        
        self.quality_data['statistics'] = stats
    
    # ==========================================
    # STATUS
    # ==========================================
    
    def status(self) -> dict:
        """Статус очереди проверок."""
        return {
            "pending_reviews": len(self.quality_data.get('pending_reviews', [])),
            "active_reviews": len(self.quality_data.get('active_reviews', [])),
            "total_history": len(self.quality_data.get('review_history', [])),
            "statistics": self.quality_data.get('statistics', {}),
            "pending_details": self.quality_data.get('pending_reviews', []),
            "active_details": self.quality_data.get('active_reviews', [])
        }
    
    def history(self, agent_name: str = None, limit: int = 10) -> dict:
        """История проверок."""
        history = self.quality_data.get('review_history', [])
        
        if agent_name:
            # Фильтровать по агенту
            filtered = []
            for h in history:
                if agent_name in h.get('worker', '') or agent_name in h.get('reviewer', ''):
                    filtered.append(h)
            history = filtered
        
        return {
            "total": len(history),
            "history": history[-limit:] if limit else history
        }


def print_help():
    print("""
🔍 Quality Gate - Система проверки качества

Команды:

  submit <task_id>
    Отправить задачу на review
    
  take-review
    Взять следующую задачу на review
    
  approve <task_id> --rating <1-5>
    Одобрить задачу
    
  reject <task_id> --reason "text"
    Отклонить задачу
    
  status
    Статус очереди
    
  history [agent_name]
    История проверок

Примеры:

  # Worker отправляет на review
  python scripts/quality_gate.py submit QS-001
  
  # Reviewer берёт задачу
  python scripts/quality_gate.py take-review
  
  # Approve
  python scripts/quality_gate.py approve QS-001 --rating 5
  
  # Reject
  python scripts/quality_gate.py reject QS-001 --reason "Tests failing"
  
  # Status
  python scripts/quality_gate.py status
""")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    gate = QualityGate()
    
    if command == "submit":
        if len(sys.argv) < 3:
            print("❌ Usage: submit <task_id>")
            sys.exit(1)
        result = gate.submit_for_review(sys.argv[2])
        
    elif command == "take-review":
        reviewer = sys.argv[2] if len(sys.argv) > 2 else None
        result = gate.take_review(reviewer)
        
    elif command == "approve":
        if len(sys.argv) < 3:
            print("❌ Usage: approve <task_id> --rating <1-5>")
            sys.exit(1)
        
        task_id = sys.argv[2]
        rating = 5
        reviewer = "Unknown Reviewer"
        
        # Parse args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == '--rating' and i + 1 < len(sys.argv):
                rating = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == '--reviewer' and i + 1 < len(sys.argv):
                reviewer = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        result = gate.approve(task_id, reviewer, rating)
        
    elif command == "reject":
        if len(sys.argv) < 3:
            print("❌ Usage: reject <task_id> --reason 'text'")
            sys.exit(1)
        
        task_id = sys.argv[2]
        reason = "Not specified"
        reviewer = "Unknown Reviewer"
        
        # Parse args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == '--reason' and i + 1 < len(sys.argv):
                reason = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--reviewer' and i + 1 < len(sys.argv):
                reviewer = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        result = gate.reject(task_id, reviewer, reason)
        
    elif command == "status":
        result = gate.status()
        
    elif command == "history":
        agent_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = gate.history(agent_name)
        
    elif command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)
        
    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        sys.exit(1)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
