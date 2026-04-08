"""Cross-layer integration tests for worktree closure.

Validates four end-to-end chains through the worktree subsystem:
  Chain 1: detect_worktree → preflight_repo_state (worktree flagged)
  Chain 2: detect_worktree → prepare_task_branch (WORKTREE_SKIP)
  Chain 3: detect_worktree → worktree-init → symlinks verified
  Chain 4: non-worktree does NOT trigger worktree logic

Mock boundary: ``harness.core.worktree.run_git`` and
``harness.core.worktree.current_branch`` are patched (git subprocess layer).
File-system I/O (symlinks, directories) uses real ``tmp_path``.
Assertions target ``GitOperationResult.context`` dicts and ``WorktreeInfo``
dataclass fields.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from harness.commands.worktree_init import _SYMLINK_TARGETS, run_worktree_init
from harness.core.worktree import WorktreeInfo, detect_worktree


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_worktree_layout(tmp_path: Path):
    """Create a fake main-repo + linked-worktree directory pair.

    Returns (main_root, linked_root, common_dir, git_dir).
    """
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    (main_root / ".git").mkdir()

    harness_dir = main_root / ".harness-flow"
    harness_dir.mkdir()
    (harness_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[workflow]\nbranch_prefix = "agent"\ntrunk_branch = "main"\n'
    )

    for rel in _SYMLINK_TARGETS:
        d = main_root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "placeholder.txt").write_text("present")

    linked_root = tmp_path / "linked-wt"
    linked_root.mkdir()

    common_dir = main_root / ".git"
    git_dir = main_root / ".git" / "worktrees" / "linked-wt"
    git_dir.mkdir(parents=True)

    return main_root, linked_root, common_dir, git_dir


def _git_mock_factory(common: Path, gitdir: Path):
    """Return a mock for ``run_git`` that simulates worktree rev-parse output."""
    calls = iter([str(common), str(gitdir)])

    def _mock(args, cwd, *, timeout=30):
        return subprocess.CompletedProcess(args, 0, stdout=next(calls))

    return _mock


def _git_mock_same_dir(directory: Path):
    """Return a mock for ``run_git`` where common_dir == git_dir (non-worktree)."""

    def _mock(args, cwd, *, timeout=30):
        return subprocess.CompletedProcess(args, 0, stdout=str(directory))

    return _mock


# ---------------------------------------------------------------------------
# Chain 1: detect → preflight (worktree context populated)
# ---------------------------------------------------------------------------

class TestChain1DetectToPreflight:
    """preflight_repo_state must set worktree=true and extract branch_task_key."""

    def test_preflight_flags_worktree_and_task_key(self, tmp_path: Path):
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)
        branch = "agent/task-047-worktree-closure-test"

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_factory(common, gitdir),
            ),
            patch("harness.core.worktree.current_branch", return_value=branch),
            patch(
                "harness.core.branch_lifecycle.current_branch",
                return_value=branch,
            ),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=_ok_result(),
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(linked_root)
            result = mgr.preflight_repo_state()

        assert result.ok
        assert result.context["worktree"] == "true"
        assert result.context["branch_task_key"] == "task-047"

    def test_preflight_error_when_dirty(self, tmp_path: Path):
        """Preflight in worktree still fails on dirty working tree."""
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)

        dirty_result = _fail_result("DIRTY_WORKING_TREE", "uncommitted changes")

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_factory(common, gitdir),
            ),
            patch("harness.core.worktree.current_branch", return_value="agent/task-047-x"),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=dirty_result,
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(linked_root)
            result = mgr.preflight_repo_state()

        assert not result.ok
        assert result.code == "DIRTY_WORKING_TREE"


# ---------------------------------------------------------------------------
# Chain 2: detect → prepare_task_branch (WORKTREE_SKIP)
# ---------------------------------------------------------------------------

class TestChain2DetectToPrepareSkip:
    """prepare_task_branch must return WORKTREE_SKIP in a linked worktree."""

    def test_prepare_returns_worktree_skip(self, tmp_path: Path):
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)
        branch = "agent/task-047-worktree-closure-test"

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_factory(common, gitdir),
            ),
            patch("harness.core.worktree.current_branch", return_value=branch),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=_ok_result(),
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(linked_root)
            result = mgr.prepare_task_branch("task-047", "worktree-closure-test")

        assert result.ok
        assert result.code == "WORKTREE_SKIP"

    def test_prepare_skip_includes_branch_in_context(self, tmp_path: Path):
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)
        branch = "agent/task-047-test"

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_factory(common, gitdir),
            ),
            patch("harness.core.worktree.current_branch", return_value=branch),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=_ok_result(),
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(linked_root)
            result = mgr.prepare_task_branch("task-047", "test")

        assert result.context["branch"] == branch


# ---------------------------------------------------------------------------
# Chain 3: detect → worktree-init → symlinks verified
# ---------------------------------------------------------------------------

class TestChain3DetectToInitToVerify:
    """detect_worktree confirms worktree → worktree-init creates symlinks → symlinks point to main."""

    def test_full_init_chain(self, tmp_path: Path):
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)

        wt = WorktreeInfo(common_dir=common.resolve(), git_dir=gitdir.resolve(), branch="agent/task-047-x")
        assert wt is not None

        with patch(
            "harness.commands.worktree_init.resolve_main_worktree_root",
            return_value=main_root,
        ):
            import os

            saved = os.getcwd()
            os.chdir(linked_root)
            try:
                run_worktree_init(force=False)
            finally:
                os.chdir(saved)

        for rel in _SYMLINK_TARGETS:
            target = linked_root / rel
            assert target.is_symlink(), f"{rel} should be a symlink"
            assert target.resolve() == (main_root / rel).resolve()

    def test_init_force_replaces_existing(self, tmp_path: Path):
        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)

        existing = linked_root / ".harness-flow"
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "stale.txt").write_text("stale")

        with patch(
            "harness.commands.worktree_init.resolve_main_worktree_root",
            return_value=main_root,
        ):
            import os

            saved = os.getcwd()
            os.chdir(linked_root)
            try:
                run_worktree_init(force=True)
            finally:
                os.chdir(saved)

        assert (linked_root / ".harness-flow").is_symlink()
        assert (linked_root / ".harness-flow").resolve() == (main_root / ".harness-flow").resolve()

    def test_init_fails_without_force_when_dir_exists(self, tmp_path: Path):
        from click.exceptions import Exit

        main_root, linked_root, common, gitdir = _make_worktree_layout(tmp_path)

        (linked_root / ".harness-flow").mkdir(parents=True, exist_ok=True)

        with patch(
            "harness.commands.worktree_init.resolve_main_worktree_root",
            return_value=main_root,
        ):
            import os

            saved = os.getcwd()
            os.chdir(linked_root)
            try:
                with pytest.raises(Exit):
                    run_worktree_init(force=False)
            finally:
                os.chdir(saved)


# ---------------------------------------------------------------------------
# Chain 4: non-worktree does NOT trigger worktree logic
# ---------------------------------------------------------------------------

class TestChain4NonWorktreeUnaffected:
    """In a normal (non-worktree) repo, worktree paths must not activate."""

    def test_detect_returns_none_in_normal_repo(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch(
            "harness.core.worktree.run_git",
            side_effect=_git_mock_same_dir(git_dir),
        ):
            assert detect_worktree(tmp_path) is None

    def test_preflight_shows_worktree_false(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        harness = tmp_path / ".harness-flow"
        harness.mkdir()
        (harness / "config.toml").write_text(
            '[project]\nname = "t"\n[workflow]\nbranch_prefix = "agent"\ntrunk_branch = "main"\n'
        )

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_same_dir(git_dir),
            ),
            patch("harness.core.worktree.current_branch", return_value="main"),
            patch("harness.core.branch_lifecycle.current_branch", return_value="main"),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=_ok_result(),
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(tmp_path)
            result = mgr.preflight_repo_state()

        assert result.ok
        assert result.context["worktree"] == "false"

    def test_prepare_does_not_skip_in_normal_repo(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        harness = tmp_path / ".harness-flow"
        harness.mkdir()
        (harness / "config.toml").write_text(
            '[project]\nname = "t"\n[workflow]\nbranch_prefix = "agent"\ntrunk_branch = "main"\n'
        )

        with (
            patch(
                "harness.core.worktree.run_git",
                side_effect=_git_mock_same_dir(git_dir),
            ),
            patch("harness.core.worktree.current_branch", return_value="main"),
            patch(
                "harness.core.branch_lifecycle.ensure_clean_result",
                return_value=_ok_result(),
            ),
            patch(
                "harness.core.branch_lifecycle.run_git_result",
                return_value=_ok_result(context={"branch": "agent/task-047-x", "created": "true"}),
            ),
        ):
            from harness.core.branch_lifecycle import BranchLifecycleManager

            mgr = BranchLifecycleManager.create(tmp_path)
            result = mgr.prepare_task_branch("task-047", "x")

        assert result.code != "WORKTREE_SKIP"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_result(**kwargs):
    from harness.integrations.git_ops import GitOperationResult

    return GitOperationResult(ok=True, code="OK", message="ok", **kwargs)


def _fail_result(code: str, message: str):
    from harness.integrations.git_ops import GitOperationResult

    return GitOperationResult(ok=False, code=code, message=message)
