"""Tests for harness.core.barriers — barrier mechanism for async sidecar tasks."""

from __future__ import annotations


import pytest

from harness.core.barriers import (
    BarrierStatus,
    check_barriers,
    complete_barrier,
    list_barriers,
    load_barrier,
    register_barrier,
)


@pytest.fixture
def task_dir(tmp_path):
    """Create a minimal task directory."""
    d = tmp_path / "task-099"
    d.mkdir()
    return d


class TestBarrierRegister:
    def test_creates_file(self, task_dir):
        record = register_barrier(task_dir, barrier_id="ci-run", phase="ship")
        assert record.id == "ci-run"
        assert record.status == BarrierStatus.PENDING
        path = task_dir / "barriers" / "ci-run.json"
        assert path.exists()

    def test_required_flag(self, task_dir):
        record = register_barrier(task_dir, barrier_id="coverage", phase="ship", required=True)
        assert record.required_for_gate is True

    def test_sanitizes_id(self, task_dir):
        register_barrier(task_dir, barrier_id="my/barrier", phase="ship")
        assert (task_dir / "barriers" / "my_barrier.json").exists()


class TestBarrierComplete:
    def test_completes_existing(self, task_dir):
        register_barrier(task_dir, barrier_id="test", phase="ship")
        record = complete_barrier(task_dir, barrier_id="test", status=BarrierStatus.DONE)
        assert record.status == BarrierStatus.DONE
        assert record.completed_at is not None

    def test_idempotent_complete(self, task_dir):
        register_barrier(task_dir, barrier_id="test", phase="ship")
        complete_barrier(task_dir, barrier_id="test", status=BarrierStatus.DONE)
        record = complete_barrier(task_dir, barrier_id="test", status=BarrierStatus.DONE)
        assert record.status == BarrierStatus.DONE

    def test_complete_with_error(self, task_dir):
        register_barrier(task_dir, barrier_id="test", phase="ship")
        record = complete_barrier(
            task_dir, barrier_id="test",
            status=BarrierStatus.FAILED,
            error="timeout",
        )
        assert record.status == BarrierStatus.FAILED
        assert record.error == "timeout"

    def test_complete_nonexistent_creates(self, task_dir):
        record = complete_barrier(task_dir, barrier_id="ghost", status=BarrierStatus.SKIPPED)
        assert record.status == BarrierStatus.SKIPPED
        assert (task_dir / "barriers" / "ghost.json").exists()


class TestBarrierLoad:
    def test_load_existing(self, task_dir):
        register_barrier(task_dir, barrier_id="test", phase="ship", required=True)
        record = load_barrier(task_dir, "test")
        assert record is not None
        assert record.required_for_gate is True

    def test_load_nonexistent(self, task_dir):
        assert load_barrier(task_dir, "nope") is None


class TestBarrierCheck:
    def test_no_barriers_dir(self, task_dir):
        result = check_barriers(task_dir)
        assert result.all_required_done is True
        assert result.total == 0

    def test_all_required_done(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        register_barrier(task_dir, barrier_id="b", phase="ship", required=True)
        complete_barrier(task_dir, barrier_id="a", status=BarrierStatus.DONE)
        complete_barrier(task_dir, barrier_id="b", status=BarrierStatus.DONE)
        result = check_barriers(task_dir, required_only=True)
        assert result.all_required_done is True

    def test_required_not_done(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        register_barrier(task_dir, barrier_id="b", phase="ship", required=True)
        complete_barrier(task_dir, barrier_id="a", status=BarrierStatus.DONE)
        result = check_barriers(task_dir, required_only=True)
        assert result.all_required_done is False
        assert "b" in result.required_not_done

    def test_required_failed(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        complete_barrier(task_dir, barrier_id="a", status=BarrierStatus.FAILED)
        result = check_barriers(task_dir, required_only=True)
        assert result.all_required_done is False

    def test_corrupted_json(self, task_dir):
        barriers_dir = task_dir / "barriers"
        barriers_dir.mkdir()
        (barriers_dir / "bad.json").write_text("not json{{{", encoding="utf-8")
        result = check_barriers(task_dir)
        assert result.unknown >= 1
        assert result.all_required_done is False

    def test_phase_filter(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship", required=True)
        register_barrier(task_dir, barrier_id="b", phase="build", required=True)
        complete_barrier(task_dir, barrier_id="a", status=BarrierStatus.DONE)
        result = check_barriers(task_dir, phase="ship", required_only=True)
        assert result.all_required_done is True
        assert result.total == 1

    def test_to_dict(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship")
        result = check_barriers(task_dir)
        d = result.to_dict()
        assert "all_required_done" in d
        assert "barriers" in d


class TestBarrierList:
    def test_empty(self, task_dir):
        assert list_barriers(task_dir) == []

    def test_lists_all(self, task_dir):
        register_barrier(task_dir, barrier_id="a", phase="ship")
        register_barrier(task_dir, barrier_id="b", phase="build")
        records = list_barriers(task_dir)
        assert len(records) == 2
        ids = {r.id for r in records}
        assert ids == {"a", "b"}
