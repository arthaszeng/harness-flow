"""Git branch operations."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def current_branch(cwd: Path) -> str:
    result = _run_git(["branch", "--show-current"], cwd)
    return result.stdout.strip()


def create_branch(branch: str, cwd: Path) -> bool:
    """Create and switch to a new branch, or switch if it already exists."""
    result = _run_git(["checkout", "-b", branch], cwd)
    if result.returncode != 0:
        # Branch exists; switch to it
        result = _run_git(["checkout", branch], cwd)
    return result.returncode == 0


def switch_branch(branch: str, cwd: Path) -> bool:
    result = _run_git(["checkout", branch], cwd)
    return result.returncode == 0


def merge_branch(source: str, target: str, cwd: Path) -> bool:
    """Merge source into target."""
    _run_git(["checkout", target], cwd)
    result = _run_git(["merge", source, "--no-ff", "-m", f"merge: {source} → {target}"], cwd)
    return result.returncode == 0


def has_changes(cwd: Path) -> bool:
    """Return True if the working tree has uncommitted changes."""
    result = _run_git(["status", "--porcelain"], cwd)
    return bool(result.stdout.strip())


def get_diff_stat(cwd: Path) -> str:
    """Get diff stat for the current branch relative to main."""
    result = _run_git(["diff", "--stat", "HEAD~1"], cwd)
    return result.stdout.strip() if result.returncode == 0 else ""


def stash_save(cwd: Path) -> bool:
    result = _run_git(["stash", "save", "harness-autosave"], cwd)
    return result.returncode == 0


def stash_pop(cwd: Path) -> bool:
    result = _run_git(["stash", "pop"], cwd)
    return result.returncode == 0
