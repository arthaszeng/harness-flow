"""Task archival — move finished work from tasks/ to archive/."""

from __future__ import annotations

import shutil
from pathlib import Path


def archive_task(agents_dir: Path, task_id: str) -> Path:
    """Move a completed task directory from tasks/ to archive/."""
    src = agents_dir / "tasks" / task_id
    if not src.exists():
        return src

    dst = agents_dir / "archive" / task_id
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))
    return dst


def ensure_task_dir(agents_dir: Path, task_id: str) -> Path:
    """Ensure the task directory exists under tasks/."""
    task_dir = agents_dir / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir
