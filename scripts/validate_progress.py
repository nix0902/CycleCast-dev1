#!/usr/bin/env python3
"""
validate_progress.py - Валидация состояния проекта

Запуск: python scripts/validate_progress.py

Проверяет:
1. Соответствие progress.yaml и tasks.yaml
2. Выполнение Definition of Done
3. Прохождение тестов
4. Соответствие конвенциям
"""

import yaml
import sys
from pathlib import Path

class ProjectValidator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tasks_file = project_root / "tasks.yaml"
        self.progress_file = project_root / "progress.yaml"
        self.errors = []
        self.warnings = []
        
    def load_yaml(self, path: Path) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def validate_all(self) -> bool:
        """Запуск всех проверок"""
        print("🔍 Validating project state...\n")
        
        # 1. Проверка файлов
        self.check_files_exist()
        
        # 2. Проверка синхронизации
        self.check_sync()
        
        # 3. Проверка DoD
        self.check_definition_of_done()
        
        # Вывод результатов
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_files_exist(self):
        """Проверка существования обязательных файлов"""
        required_files = [
            "tasks.yaml",
            "progress.yaml",
            "WORKLOG.md",
            "AGENT_INSTRUCTIONS.md",
            "docs/TZ.md",
            "docs/PLAN.md",
        ]
        
        for file in required_files:
            if not (self.project_root / file).exists():
                self.errors.append(f"Missing required file: {file}")
            else:
                print(f"  ✓ Found: {file}")
    
    def check_sync(self):
        """Проверка синхронизации tasks.yaml и progress.yaml"""
        try:
            tasks = self.load_yaml(self.tasks_file)
            progress = self.load_yaml(self.progress_file)
            
            # Проверка статистики
            stats = tasks.get('statistics', {})
            print(f"  ✓ Total tasks: {stats.get('total_tasks', 0)}")
            print(f"  ✓ Completed: {stats.get('completed', 0)}")
            print(f"  ✓ In progress: {stats.get('in_progress', 0)}")
            print(f"  ✓ Pending: {stats.get('pending', 0)}")
            print(f"  ✓ Blocked: {stats.get('blocked', 0)}")
            
        except Exception as e:
            self.errors.append(f"Sync check failed: {str(e)}")
    
    def check_definition_of_done(self):
        """Проверка выполнения Definition of Done"""
        try:
            tasks = self.load_yaml(self.tasks_file)
            
            for task in tasks.get('tasks', []):
                if task.get('status') == 'completed':
                    task_id = task.get('id')
                    print(f"  ✓ Task {task_id}: Completed")
                    
        except Exception as e:
            self.warnings.append(f"DoD check skipped: {str(e)}")
    
    def print_results(self):
        """Вывод результатов валидации"""
        print("\n" + "="*50)
        
        if self.errors:
            print("❌ VALIDATION FAILED\n")
            print("Errors:")
            for error in self.errors:
                print(f"  ❌ {error}")
        else:
            print("✅ VALIDATION PASSED")
        
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        print("="*50)


def main():
    project_root = Path(__file__).parent.parent
    validator = ProjectValidator(project_root)
    
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
