"""Worktree detection for Cursor parallel agents.

Detects whether the current working directory is inside a git worktree
(as opposed to the main working tree), and provides worktree metadata
for task isolation and status display.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from harness.integrations.git_ops import current_branch, run_git

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorktreeInfo:
    """Metadata about the current git worktree."""

    common_dir: Path
    git_dir: Path
    branch: str


def detect_worktree(cwd: Path | None = None) -> WorktreeInfo | None:
    """Detect if *cwd* is inside a Cursor parallel-agent worktree.

    Returns ``WorktreeInfo`` when the git common dir differs from the git dir
    (indicating a linked worktree), or ``None`` for the main working tree or
    when git is unavailable.
    """
    root = cwd or Path.cwd()
    try:
        common_result = run_git(["rev-parse", "--git-common-dir"], root, timeout=5)
        git_result = run_git(["rev-parse", "--git-dir"], root, timeout=5)
    except Exception:
        log.debug("git subprocess failed during worktree detection", exc_info=True)
        return None

    if common_result.returncode != 0 or git_result.returncode != 0:
        return None

    raw_common = Path(common_result.stdout.strip())
    raw_git = Path(git_result.stdout.strip())
    common_dir = (raw_common if raw_common.is_absolute() else (root / raw_common)).resolve()
    git_dir = (raw_git if raw_git.is_absolute() else (root / raw_git)).resolve()

    if common_dir == git_dir:
        return None

    try:
        branch = current_branch(root)
    except Exception:
        branch = ""

    return WorktreeInfo(common_dir=common_dir, git_dir=git_dir, branch=branch)


def extract_task_id_from_branch(branch: str) -> str | None:
    """Extract ``task-NNN`` from an ``agent/task-NNN-*`` branch name.

    Returns ``None`` if the branch does not match the expected pattern.
    """
    import re

    m = re.match(r"agent/(task-\d+)", branch)
    return m.group(1) if m else None
