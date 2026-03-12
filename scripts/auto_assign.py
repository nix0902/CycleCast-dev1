#!/usr/bin/env python3
"""
auto_assign.py - Автоматическое распределение задач между агентами

Команды:
    python scripts/auto_assign.py assign <task_id>
    python scripts/auto_assign.py assign-all
    python scripts/auto_assign.py recommend <task_id>
    python scripts/auto_assign.py agent-profile <agent_name>
    python scripts/auto_assign.py update-stats
"""

import yaml
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import random


class AutoAssigner:
    """Автоматическое распределение задач между ИИ-агентами."""
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
        self.tasks_file = project_root / "tasks.yaml"
        self.skills_file = project_root / "agent_skills.yaml"
        self.session_file = project_root / "session.yaml"
        
        # Загрузка данных
        self.tasks_data = self._load_yaml(self.tasks_file)
        self.skills_data = self._load_yaml(self.skills_file)
        self.session_data = self._load_yaml(self.session_file)
        
        # Конфигурация
        self.config = self.skills_data.get('config', {})
        self.weights = self.config.get('scoring_weights', {
            'skills_match': 0.40,
            'specialization_match': 0.25,
            'performance_score': 0.20,
            'load_balance': 0.15
        })
    
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
    # СКОРИНГ
    # ==========================================
    
    def calculate_skills_match(self, agent: dict, task: dict) -> float:
        """
        Расчёт соответствия навыков агента требованиям задачи.
        
        Returns:
            float: 0.0 - 1.0 (процент соответствия)
        """
        required_skills = task.get('required_skills', [])
        if not required_skills:
            return 1.0  # Нет требований = полное соответствие
        
        agent_skills = {s['name']: s['level'] for s in agent.get('skills', [])}
        
        matched = 0
        total = len(required_skills)
        
        for req in required_skills:
            skill_name = req.get('name')
            min_level = req.get('min_level', 1)
            
            agent_level = agent_skills.get(skill_name, 0)
            
            if agent_level >= min_level:
                # Полное соответствие или выше
                matched += 1
            elif agent_level > 0:
                # Частичное соответствие
                matched += agent_level / min_level * 0.5
        
        return matched / total if total > 0 else 1.0
    
    def calculate_specialization_match(self, agent: dict, task: dict) -> float:
        """
        Расчёт соответствия специализации.
        
        Returns:
            float: 0.5 - 1.0
        """
        task_type = task.get('task_type', '')
        preferred_specs = task.get('preferred_specializations', [])
        
        agent_specs = agent.get('specializations', [])
        
        # Проверяем task_type
        if task_type in agent_specs:
            return 1.0
        
        # Проверяем preferred_specializations
        for spec in preferred_specs:
            if spec in agent_specs:
                return 1.0
        
        return 0.5
    
    def calculate_performance_score(self, agent: dict) -> float:
        """
        Расчёт оценки производительности агента.
        
        Returns:
            float: 0.0 - 1.0
        """
        perf = agent.get('performance', {})
        success_rate = perf.get('success_rate', 0.5)
        time_factor = perf.get('avg_completion_time_factor', 1.0)
        
        # Выше success_rate и ниже time_factor = лучше
        # time_factor < 1 = быстрее среднего
        time_score = max(0, 1.0 - (time_factor - 0.5))  # Нормализация
        
        return success_rate * time_score
    
    def calculate_load_balance(self, agent: dict) -> float:
        """
        Расчёт фактора балансировки нагрузки.
        
        Returns:
            float: 0.0 - 1.0 (меньше задач = выше score)
        """
        load = agent.get('current_load', {})
        active_tasks = load.get('active_tasks', 0)
        max_tasks = self.config.get('max_tasks_per_agent', 3)
        
        if active_tasks >= max_tasks:
            return 0.0
        
        return 1.0 / (active_tasks + 1)
    
    def calculate_agent_score(self, agent: dict, task: dict) -> Tuple[float, dict]:
        """
        Полный расчёт скоринга агента для задачи.
        
        Returns:
            Tuple[float, dict]: (total_score, breakdown)
        """
        skills_match = self.calculate_skills_match(agent, task)
        spec_match = self.calculate_specialization_match(agent, task)
        perf_score = self.calculate_performance_score(agent)
        load_balance = self.calculate_load_balance(agent)
        
        total = (
            skills_match * self.weights['skills_match'] +
            spec_match * self.weights['specialization_match'] +
            perf_score * self.weights['performance_score'] +
            load_balance * self.weights['load_balance']
        )
        
        breakdown = {
            'skills_match': round(skills_match, 3),
            'specialization_match': round(spec_match, 3),
            'performance_score': round(perf_score, 3),
            'load_balance': round(load_balance, 3),
            'total': round(total, 3)
        }
        
        return total, breakdown
    
    # ==========================================
    # НАЗНАЧЕНИЕ
    # ==========================================
    
    def recommend(self, task_id: str) -> dict:
        """
        Рекомендация лучшего агента без назначения.
        """
        # Найти задачу
        task = None
        for t in self.tasks_data.get('tasks', []):
            if t.get('id') == task_id:
                task = t
                break
        
        if not task:
            return {
                "success": False,
                "error": f"Task {task_id} not found"
            }
        
        # Проверить статус
        if task.get('status') != 'pending':
            return {
                "success": False,
                "error": f"Task {task_id} is not pending (status: {task.get('status')})"
            }
        
        # Рассчитать скоринг для всех агентов
        agents = self.skills_data.get('agents', {})
        scores = []
        
        for agent_name, agent_data in agents.items():
            # Пропустить недоступных
            if not agent_data.get('current_load', {}).get('available', True):
                continue
            
            # Проверить предпочтения
            prefs = agent_data.get('preferences', {})
            task_type = task.get('task_type', '')
            avoid_types = prefs.get('avoid_task_types', [])
            
            if task_type in avoid_types:
                continue
            
            score, breakdown = self.calculate_agent_score(agent_data, task)
            
            if score >= self.config.get('min_score_threshold', 0.5):
                scores.append({
                    'agent': agent_name,
                    'score': score,
                    'breakdown': breakdown
                })
        
        # Сортировать по score
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            "success": True,
            "task_id": task_id,
            "task_title": task.get('title'),
            "recommendations": scores[:5],  # Топ-5
            "total_qualified_agents": len(scores)
        }
    
    def assign(self, task_id: str, force: bool = False) -> dict:
        """
        Назначение задачи лучшему агенту.
        """
        # Получить рекомендации
        rec_result = self.recommend(task_id)
        
        if not rec_result.get('success'):
            return rec_result
        
        recommendations = rec_result.get('recommendations', [])
        
        if not recommendations:
            return {
                "success": False,
                "error": "No qualified agents available",
                "task_id": task_id
            }
        
        # Выбрать лучшего
        best = recommendations[0]
        agent_name = best['agent']
        
        # Обновить tasks.yaml
        for task in self.tasks_data.get('tasks', []):
            if task.get('id') == task_id:
                task['assignee'] = agent_name
                task['assigned_at'] = self._get_timestamp()
                task['status'] = 'assigned'
                break
        
        self._save_yaml(self.tasks_file, self.tasks_data)
        
        # Обновить agent_skills.yaml (нагрузка)
        if agent_name in self.skills_data.get('agents', {}):
            agent = self.skills_data['agents'][agent_name]
            if 'current_load' not in agent:
                agent['current_load'] = {}
            agent['current_load']['reserved_tasks'] = agent['current_load'].get('reserved_tasks', 0) + 1
            self._save_yaml(self.skills_file, self.skills_data)
        
        # Обновить session.yaml
        if 'assignment_history' not in self.skills_data:
            self.skills_data['assignment_history'] = []
        
        self.skills_data['assignment_history'].append({
            'task_id': task_id,
            'agent': agent_name,
            'score': best['score'],
            'assigned_at': self._get_timestamp(),
            'status': 'pending_accept'
        })
        
        self.skills_data['statistics'] = self.skills_data.get('statistics', {})
        self.skills_data['statistics']['total_assignments'] = self.skills_data['statistics'].get('total_assignments', 0) + 1
        
        self._save_yaml(self.skills_file, self.skills_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "assigned_to": agent_name,
            "score": best['score'],
            "breakdown": best['breakdown'],
            "action": "agent_must_accept_or_decline",
            "accept_command": f"python scripts/session_manager.py register {task_id} \"{agent_name}\" model"
        }
    
    def assign_all(self) -> dict:
        """
        Назначение всех pending задач.
        """
        results = {
            "assigned": [],
            "failed": [],
            "skipped": []
        }
        
        for task in self.tasks_data.get('tasks', []):
            if task.get('status') != 'pending':
                continue
            
            task_id = task.get('id')
            result = self.assign(task_id)
            
            if result.get('success'):
                results['assigned'].append({
                    'task_id': task_id,
                    'agent': result.get('assigned_to')
                })
            else:
                results['failed'].append({
                    'task_id': task_id,
                    'reason': result.get('error')
                })
        
        return {
            "success": True,
            "summary": {
                "total_assigned": len(results['assigned']),
                "total_failed": len(results['failed']),
                "total_skipped": len(results['skipped'])
            },
            "details": results
        }
    
    def agent_profile(self, agent_name: str) -> dict:
        """
        Получить профиль агента.
        """
        agents = self.skills_data.get('agents', {})
        
        if agent_name not in agents:
            # Попробовать найти по частичному совпадению
            for name in agents:
                if agent_name.lower() in name.lower():
                    agent_name = name
                    break
            else:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "available_agents": list(agents.keys())
                }
        
        agent = agents[agent_name]
        
        return {
            "success": True,
            "agent_name": agent_name,
            "model_id": agent.get('model_id'),
            "provider": agent.get('provider'),
            "skills": agent.get('skills', []),
            "specializations": agent.get('specializations', []),
            "preferences": agent.get('preferences', {}),
            "performance": agent.get('performance', {}),
            "current_load": agent.get('current_load', {}),
            "available": agent.get('current_load', {}).get('available', True)
        }
    
    def update_stats(self, session_manager
        }
    
    def update_stats(self) -> dict:
        """
        Обновление статистики агентов на основе завершённых задач.
        """
        # Здесь можно добавить логику обновления на основе history
        return {
            "success": True,
            "message": "Stats update logic to be implemented",
            "current_stats": self.skills_data.get('statistics', {})
        }


def print_help():
    print("""
🎯 Auto-Assignment - Автоматическое распределение задач

Команды:

  assign <task_id>
    Назначить задачу лучшему агенту
    
  assign-all
    Назначить все pending задачи
    
  recommend <task_id>
    Посмотреть рекомендации (без назначения)
    
  agent-profile <agent_name>
    Профиль агента
    
  update-stats
    Обновить статистику агентов

Примеры:

  python scripts/auto_assign.py recommend QS-001
  python scripts/auto_assign.py assign QS-001
  python scripts/auto_assign.py assign-all
  python scripts/auto_assign.py agent-profile "Claude"
""")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    assigner = AutoAssigner()
    
    if command == "assign":
        if len(sys.argv) < 3:
            print("❌ Usage: assign <task_id>")
            sys.exit(1)
        result = assigner.assign(sys.argv[2])
        
    elif command == "assign-all":
        result = assigner.assign_all()
        
    elif command == "recommend":
        if len(sys.argv) < 3:
            print("❌ Usage: recommend <task_id>")
            sys.exit(1)
        result = assigner.recommend(sys.argv[2])
        
    elif command == "agent-profile":
        if len(sys.argv) < 3:
            print("❌ Usage: agent-profile <agent_name>")
            sys.exit(1)
        result = assigner.agent_profile(sys.argv[2])
        
    elif command == "update-stats":
        result = assigner.update_stats()
        
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
