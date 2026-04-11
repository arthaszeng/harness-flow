"""Tests for barrier integration in gates.py — check_ship_readiness."""

from __future__ import annotations


import pytest

from harness.core.barriers import BarrierStatus, complete_barrier, register_barrier
from harness.core.gates import CheckStatus, _check_barrier_readiness


@pytest.fixture
def task_dir(tmp_path):
    d = tmp_path / "task-099"
    d.mkdir()
    (d / "plan.md").write_text("# Spec\n## Verdict: PASS")
    return d


class TestBarrierGateIntegration:
    def test_no_barriers_dir_returns_none(self, task_dir):
        result = _check_barrier_readiness(task_dir)
        assert result is None

    def test_empty_barriers_dir_returns_none(self, task_dir):
        (task_dir / "barriers").mkdir()
        result = _check_barrier_readiness(task_dir)
        assert result is None

    def test_all_required_done_passes(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        complete_barrier(task_dir, barrier_id="a", status=BarrierStatus.DONE)
        result = _check_barrier_readiness(task_dir)
        assert result is not None
        assert result.status == CheckStatus.PASS

    def test_required_not_done_blocks(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        result = _check_barrier_readiness(task_dir)
        assert result is not None
        assert result.status == CheckStatus.BLOCKED
        assert "a" in result.reason

    def test_non_required_not_counted(self, task_dir):
        register_barrier(task_dir, barrier_id="optional", phase="ship", required=False)
        result = _check_barrier_readiness(task_dir)
        assert result is None
