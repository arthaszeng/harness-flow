"""Tests for harness.core.worktree — worktree detection and task-id extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest

from harness.core.worktree import WorktreeInfo, detect_worktree, extract_task_id_from_branch


class TestDetectWorktree:
    def test_returns_none_in_normal_repo(self, tmp_path: Path):
        """Non-worktree (same common_dir and git_dir) returns None."""
        fake_git_dir = str(tmp_path / ".git")

        def mock_run(args, cwd, *, timeout=30):
            result = subprocess.CompletedProcess(args, 0)
            result.stdout = fake_git_dir
            return result

        with patch("harness.core.worktree.run_git", side_effect=mock_run):
            assert detect_worktree(tmp_path) is None

    def test_returns_info_in_worktree(self, tmp_path: Path):
        """Different common_dir vs git_dir signals a worktree."""
        common = tmp_path / "main-repo" / ".git"
        common.mkdir(parents=True)
        gitdir = tmp_path / "worktree" / ".git"
        gitdir.mkdir(parents=True)

        calls = iter([str(common), str(gitdir)])

        def mock_run(args, cwd, *, timeout=30):
            result = subprocess.CompletedProcess(args, 0)
            result.stdout = next(calls)
            return result

        with (
            patch("harness.core.worktree.run_git", side_effect=mock_run),
            patch("harness.core.worktree.current_branch", return_value="agent/task-042-feature"),
        ):
            info = detect_worktree(tmp_path)
            assert info is not None
            assert isinstance(info, WorktreeInfo)
            assert info.common_dir == common.resolve()
            assert info.git_dir == gitdir.resolve()
            assert info.branch == "agent/task-042-feature"

    def test_returns_none_on_git_failure(self, tmp_path: Path):
        """Git subprocess failure returns None gracefully."""
        def mock_run(args, cwd, *, timeout=30):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="not a repo")

        with patch("harness.core.worktree.run_git", side_effect=mock_run):
            assert detect_worktree(tmp_path) is None

    def test_returns_none_on_exception(self, tmp_path: Path):
        """Unhandled exception returns None."""
        with patch("harness.core.worktree.run_git", side_effect=OSError("nope")):
            assert detect_worktree(tmp_path) is None

    def test_resolves_relative_paths_against_cwd(self, tmp_path: Path):
        """Git may return relative paths; they should resolve against cwd."""
        calls = iter([".git", "../other/.git"])

        def mock_run(args, cwd, *, timeout=30):
            result = subprocess.CompletedProcess(args, 0)
            result.stdout = next(calls)
            return result

        with (
            patch("harness.core.worktree.run_git", side_effect=mock_run),
            patch("harness.core.worktree.current_branch", return_value="main"),
        ):
            info = detect_worktree(tmp_path)
            assert info is not None
            assert info.common_dir == (tmp_path / ".git").resolve()
            assert info.git_dir == (tmp_path / "../other/.git").resolve()


class TestExtractTaskIdFromBranch:
    @pytest.mark.parametrize("branch,expected", [
        ("agent/task-001-feature", "task-001"),
        ("agent/task-42-short", "task-42"),
        ("agent/task-999-long-name-here", "task-999"),
        ("agent/PROJ-123-improve-git", "PROJ-123"),
        ("main", None),
        ("feature/something", None),
        ("agent/no-task-here", None),
        ("", None),
    ])
    def test_patterns(self, branch: str, expected: str | None):
        assert extract_task_id_from_branch(branch) == expected
