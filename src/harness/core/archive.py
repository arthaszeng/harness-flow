"""任务归档 — active → archive + summary"""

from __future__ import annotations

import shutil
from pathlib import Path


def archive_task(agents_dir: Path, task_id: str) -> Path:
    """将已完成的任务从 tasks/ 移到 archive/"""
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
    """确保任务目录存在"""
    task_dir = agents_dir / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir
