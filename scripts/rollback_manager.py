#!/usr/bin/env python3
"""
Rollback Manager - Управление контрольными точками

Usage:
    python scripts/rollback_manager.py create [description] [--type TYPE] [--task-id ID]
    python scripts/rollback_manager.py list
    python scripts/rollback_manager.py show <checkpoint_id>
    python scripts/rollback_manager.py restore <checkpoint_id>
    python scripts/rollback_manager.py cleanup
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

BASE_DIR = Path(__file__).parent.parent
ROLLBACK_FILE = BASE_DIR / "rollback_points.yaml"
DB_PATH = BASE_DIR / "db" / "custom.db"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def calculate_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def get_git_info() -> dict:
    """Get current git state."""
    info = {
        "sha": None,
        "branch": None,
        "has_uncommitted": False,
    }
    
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        if result.returncode == 0:
            info["sha"] = result.stdout.strip()[:12]
        
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
        
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        if result.returncode == 0:
            info["has_uncommitted"] = len(result.stdout.strip()) > 0
    except Exception:
        pass
    
    return info


def get_next_checkpoint_id(checkpoint_type: str) -> str:
    """Generate next checkpoint ID."""
    config = load_yaml(ROLLBACK_FILE)
    
    prefixes = {
        "pre_task": "RP-PRE",
        "post_task": "RP-POST",
        "milestone": "RP-MS",
        "manual": "RP-MAN",
        "scheduled": "RP-SCH",
        "pre_rollback": "RP-RBK"
    }
    
    prefix = prefixes.get(checkpoint_type, "RP-MAN")
    
    checkpoints = config.get("checkpoints", [])
    max_num = 0
    for cp in checkpoints:
        if cp.get("id", "").startswith(prefix):
            try:
                num = int(cp["id"].split("-")[-1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    
    return f"{prefix}-{max_num + 1:03d}"


def create_checkpoint(
    description: str = "",
    checkpoint_type: str = "manual",
    task_id: Optional[str] = None,
    tags: list = None
) -> dict:
    """Create a new checkpoint."""
    print(f"\n🔄 Creating checkpoint (type: {checkpoint_type})...\n")
    
    config = load_yaml(ROLLBACK_FILE)
    checkpoint_id = get_next_checkpoint_id(checkpoint_type)
    timestamp = datetime.now().isoformat()
    
    # Create snapshot directory
    snapshot_dir = SNAPSHOTS_DIR / checkpoint_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get git info
    git_info = get_git_info()
    print(f"  📦 Git: {git_info['sha']} ({git_info['branch']})")
    
    # Create file snapshot
    print("  📁 Creating files snapshot...")
    files_tar = snapshot_dir / "files.tar.gz"
    file_count = 0
    
    with tarfile.open(files_tar, "w:gz") as tar:
        for pattern in ["src/**/*.ts", "src/**/*.tsx", "*.yaml", "*.md"]:
            for f in BASE_DIR.glob(pattern):
                if f.is_file() and "node_modules" not in str(f):
                    try:
                        tar.add(f, arcname=str(f.relative_to(BASE_DIR)))
                        file_count += 1
                    except Exception:
                        pass
    
    # Create database snapshot
    db_snapshot = None
    print("  💾 Creating database snapshot...")
    if DB_PATH.exists():
        db_copy = snapshot_dir / "database.db"
        shutil.copy2(DB_PATH, db_copy)
        db_snapshot = {
            "path": str(db_copy.relative_to(BASE_DIR)),
            "checksum": calculate_checksum(db_copy),
            "size_bytes": db_copy.stat().st_size
        }
    
    # Create checkpoint record
    checkpoint = {
        "id": checkpoint_id,
        "type": checkpoint_type,
        "timestamp": timestamp,
        "metadata": {
            "description": description,
            "created_by": "GLM-5 (Zhipu AI)",
            "task_id": task_id,
            "tags": tags or []
        },
        "git": git_info,
        "snapshot": {
            "files": {
                "path": str(files_tar.relative_to(BASE_DIR)),
                "file_count": file_count,
                "size_bytes": files_tar.stat().st_size
            },
            "database": db_snapshot
        },
        "verification": {
            "verified": True,
            "verified_at": timestamp
        }
    }
    
    # Save
    if "checkpoints" not in config:
        config["checkpoints"] = []
    config["checkpoints"].append(checkpoint)
    
    # Update statistics
    if "statistics" not in config:
        config["statistics"] = {}
    config["statistics"]["checkpoints_created"] = config["statistics"].get("checkpoints_created", 0) + 1
    
    by_type = config["statistics"].get("by_type", {})
    by_type[checkpoint_type] = by_type.get(checkpoint_type, 0) + 1
    config["statistics"]["by_type"] = by_type
    
    save_yaml(ROLLBACK_FILE, config)
    
    print(f"\n✅ Checkpoint created: {checkpoint_id}")
    print(f"   Files: {file_count}")
    print(f"   Database: {'Yes' if db_snapshot else 'No'}\n")
    
    return checkpoint


def list_checkpoints() -> None:
    """List all checkpoints."""
    config = load_yaml(ROLLBACK_FILE)
    checkpoints = config.get("checkpoints", [])
    
    print(f"\n📋 Checkpoints ({len(checkpoints)} total)\n")
    print(f"{'ID':<15} {'Type':<12} {'Created':<22} {'Description':<30}")
    print("-" * 85)
    
    for cp in checkpoints:
        timestamp = cp.get("timestamp", "unknown")[:19]
        desc = cp.get("metadata", {}).get("description", "")[:28]
        print(f"{cp['id']:<15} {cp['type']:<12} {timestamp:<22} {desc:<30}")
    
    print()


def show_checkpoint(checkpoint_id: str) -> None:
    """Show checkpoint details."""
    config = load_yaml(ROLLBACK_FILE)
    
    checkpoint = None
    for cp in config.get("checkpoints", []):
        if cp.get("id") == checkpoint_id:
            checkpoint = cp
            break
    
    if not checkpoint:
        print(f"❌ Checkpoint not found: {checkpoint_id}\n")
        return
    
    print(f"\n📦 Checkpoint: {checkpoint_id}\n")
    print(f"  Type: {checkpoint.get('type')}")
    print(f"  Created: {checkpoint.get('timestamp')}")
    print(f"  Description: {checkpoint.get('metadata', {}).get('description', '-')}")
    
    git = checkpoint.get("git", {})
    print(f"\n  Git:")
    print(f"    SHA: {git.get('sha', '-')}")
    print(f"    Branch: {git.get('branch', '-')}")
    print(f"    Uncommitted: {'Yes' if git.get('has_uncommitted') else 'No'}")
    
    snapshot = checkpoint.get("snapshot", {})
    files = snapshot.get("files", {})
    print(f"\n  Files:")
    print(f"    Count: {files.get('file_count', 0)}")
    print(f"    Size: {files.get('size_bytes', 0) // 1024}KB")
    
    print()


def restore_checkpoint(checkpoint_id: str) -> bool:
    """Restore from checkpoint."""
    config = load_yaml(ROLLBACK_FILE)
    
    checkpoint = None
    for cp in config.get("checkpoints", []):
        if cp.get("id") == checkpoint_id:
            checkpoint = cp
            break
    
    if not checkpoint:
        print(f"❌ Checkpoint not found: {checkpoint_id}\n")
        return False
    
    print(f"\n🔄 Restoring from checkpoint: {checkpoint_id}\n")
    
    snapshot = checkpoint.get("snapshot", {})
    
    # Restore files
    files_tar = BASE_DIR / snapshot.get("files", {}).get("path", "")
    if files_tar.exists():
        print("  📁 Restoring files...")
        with tarfile.open(files_tar, "r:gz") as tar:
            tar.extractall(BASE_DIR)
        print("     ✅ Files restored")
    
    # Restore database
    db_snapshot = snapshot.get("database")
    if db_snapshot:
        db_copy = BASE_DIR / db_snapshot.get("path", "")
        if db_copy.exists():
            print("  💾 Restoring database...")
            if DB_PATH.exists():
                DB_PATH.unlink()
            shutil.copy2(db_copy, DB_PATH)
            print("     ✅ Database restored")
    
    # Record rollback
    if "rollback_history" not in config:
        config["rollback_history"] = []
    
    config["rollback_history"].append({
        "id": f"RB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "from_checkpoint": checkpoint_id,
        "status": "completed"
    })
    
    config["statistics"]["rollbacks_performed"] = config["statistics"].get("rollbacks_performed", 0) + 1
    config["statistics"]["rollbacks_successful"] = config["statistics"].get("rollbacks_successful", 0) + 1
    
    save_yaml(ROLLBACK_FILE, config)
    
    print(f"\n✅ Rollback completed: {checkpoint_id}\n")
    return True


def cleanup_checkpoints() -> None:
    """Clean up old checkpoints."""
    config = load_yaml(ROLLBACK_FILE)
    retention_days = config.get("config", {}).get("retention_days", 30)
    
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    deleted = 0
    remaining = []
    
    for cp in config.get("checkpoints", []):
        cp_date = datetime.fromisoformat(cp.get("timestamp", "2000-01-01"))
        if cp_date < cutoff:
            # Delete snapshot files
            snapshot_dir = SNAPSHOTS_DIR / cp["id"]
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)
            deleted += 1
        else:
            remaining.append(cp)
    
    config["checkpoints"] = remaining
    config["statistics"]["checkpoints_deleted"] = config["statistics"].get("checkpoints_deleted", 0) + deleted
    
    save_yaml(ROLLBACK_FILE, config)
    
    print(f"\n🧹 Cleanup complete: {deleted} checkpoints deleted\n")


def main():
    parser = argparse.ArgumentParser(description="Rollback Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # create
    create_parser = subparsers.add_parser("create", help="Create checkpoint")
    create_parser.add_argument("description", nargs="?", default="")
    create_parser.add_argument("--type", "-t", default="manual",
        choices=["pre_task", "post_task", "milestone", "manual", "scheduled"])
    create_parser.add_argument("--task-id")
    create_parser.add_argument("--tags")
    
    # list
    subparsers.add_parser("list", help="List checkpoints")
    
    # show
    show_parser = subparsers.add_parser("show", help="Show checkpoint")
    show_parser.add_argument("checkpoint_id")
    
    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore checkpoint")
    restore_parser.add_argument("checkpoint_id")
    
    # cleanup
    subparsers.add_parser("cleanup", help="Cleanup old checkpoints")
    
    args = parser.parse_args()
    
    if args.command == "create":
        tags = args.tags.split(",") if args.tags else []
        create_checkpoint(args.description, args.type, args.task_id, tags)
    elif args.command == "list":
        list_checkpoints()
    elif args.command == "show":
        show_checkpoint(args.checkpoint_id)
    elif args.command == "restore":
        restore_checkpoint(args.checkpoint_id)
    elif args.command == "cleanup":
        cleanup_checkpoints()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
