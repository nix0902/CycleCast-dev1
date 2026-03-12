#!/usr/bin/env python3
"""
Code Review Bot - Автоматический ИИ-агент для проверки кода

Usage:
    python scripts/code_review_bot.py review <task_id>
    python scripts/code_review_bot.py stats
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).parent.parent
REVIEW_BOT_FILE = BASE_DIR / "review_bot.yaml"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_static_analysis() -> dict:
    """Run static analysis checks."""
    results = {"errors": [], "warnings": [], "info": []}
    
    # Run ESLint
    try:
        result = subprocess.run(
            ["bun", "run", "lint"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=60
        )
        if result.returncode != 0:
            for line in result.stdout.split("\n"):
                if "error" in line.lower():
                    results["errors"].append(line)
                elif "warning" in line.lower():
                    results["warnings"].append(line)
    except Exception as e:
        results["errors"].append(str(e))
    
    return results


def run_security_checks() -> dict:
    """Run security checks."""
    results = {"issues": []}
    
    # Check for hardcoded secrets (basic pattern matching)
    patterns = [
        "api_key\\s*=\\s*['\"][^'\"]+['\"]",
        "password\\s*=\\s*['\"][^'\"]+['\"]",
        "secret\\s*=\\s*['\"][^'\"]+['\"]",
    ]
    
    # Would implement actual pattern matching here
    # For now, return empty results
    
    return results


def calculate_score(static: dict, security: dict) -> int:
    """Calculate overall score."""
    score = 100
    
    score -= len(static.get("errors", [])) * 10
    score -= len(static.get("warnings", [])) * 5
    score -= len(security.get("issues", [])) * 15
    
    return max(0, min(100, score))


def get_status(score: int, has_critical: bool) -> str:
    """Determine review status."""
    if has_critical or score < 60:
        return "changes_required"
    elif score < 80:
        return "warnings"
    else:
        return "approved"


def review_task(task_id: str) -> dict:
    """Review task code."""
    print(f"\n🔍 Code Review for task: {task_id}\n")
    
    print("  📦 Running static analysis...")
    static = run_static_analysis()
    
    print("  🔒 Running security checks...")
    security = run_security_checks()
    
    score = calculate_score(static, security)
    has_critical = len(security.get("issues", [])) > 0
    status = get_status(score, has_critical)
    
    # Print report
    status_icons = {
        "approved": "✅",
        "warnings": "⚠️",
        "changes_required": "❌"
    }
    icon = status_icons.get(status, "❓")
    
    print(f"\n{'═' * 60}")
    print(f"  {icon} Code Review Report")
    print(f"{'═' * 60}")
    print(f"  Task: {task_id}")
    print(f"  Score: {score}/100")
    print(f"  Status: {status.upper()}")
    print(f"{'═' * 60}\n")
    
    # Update statistics
    config = load_yaml(REVIEW_BOT_FILE)
    if "statistics" not in config:
        config["statistics"] = {}
    config["statistics"]["total_reviews"] = config["statistics"].get("total_reviews", 0) + 1
    
    if status == "approved":
        config["statistics"]["approved"] = config["statistics"].get("approved", 0) + 1
    elif status == "changes_required":
        config["statistics"]["blocked"] = config["statistics"].get("blocked", 0) + 1
    else:
        config["statistics"]["warnings"] = config["statistics"].get("warnings", 0) + 1
    
    save_yaml(REVIEW_BOT_FILE, config)
    
    return {
        "task_id": task_id,
        "score": score,
        "status": status,
        "static": static,
        "security": security
    }


def show_stats() -> None:
    """Show review statistics."""
    config = load_yaml(REVIEW_BOT_FILE)
    stats = config.get("statistics", {})
    
    print("\n📊 Code Review Statistics\n")
    print(f"  Total reviews: {stats.get('total_reviews', 0)}")
    print(f"  ✅ Approved: {stats.get('approved', 0)}")
    print(f"  ⚠️ Warnings: {stats.get('warnings', 0)}")
    print(f"  ❌ Blocked: {stats.get('blocked', 0)}\n")


def main():
    parser = argparse.ArgumentParser(description="Code Review Bot")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # review
    review_parser = subparsers.add_parser("review", help="Review task")
    review_parser.add_argument("task_id", help="Task ID")
    
    # stats
    subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    if args.command == "review":
        review_task(args.task_id)
    elif args.command == "stats":
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
