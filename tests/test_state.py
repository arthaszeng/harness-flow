"""state.py unit tests"""

import json
from pathlib import Path

from harness.core.progress import update_progress
from harness.core.state import (
    CompletedTask,
    SessionState,
    StopContext,
    TaskRecord,
    TaskState,
)


def test_session_save_load(tmp_path: Path):
    state = SessionState(session_id="test-001", mode="auto")
    agents_dir = tmp_path / ".agents"
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.session_id == "test-001"
    assert loaded.mode == "auto"


def test_detect_incomplete(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    assert SessionState.detect_incomplete(agents_dir) is None

    state = SessionState(
        session_id="test",
        mode="run",
        current_task=TaskRecord(id="t1", requirement="test"),
    )
    state.save(agents_dir)
    incomplete = SessionState.detect_incomplete(agents_dir)
    assert incomplete is not None
    assert incomplete.current_task.id == "t1"


def test_detect_incomplete_idle_not_resumable(tmp_path: Path):
    """Idle mode should not be treated as incomplete even with history."""
    agents_dir = tmp_path / ".agents"
    state = SessionState(session_id="s1", mode="idle", current_task=None)
    state.save(agents_dir)
    assert SessionState.detect_incomplete(agents_dir) is None


# ---------------------------------------------------------------------------
# Stop context persistence tests
# ---------------------------------------------------------------------------


def test_stop_context_backward_compat(tmp_path: Path):
    """Old state.json without stop_context should load() normally."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    old_state = {
        "session_id": "legacy-001",
        "mode": "auto",
        "current_task": None,
        "completed": [],
        "blocked": [],
        "stats": {
            "total_tasks": 0, "completed": 0, "blocked": 0,
            "total_iterations": 0, "avg_score": 0.0, "elapsed_seconds": 0.0,
        },
    }
    (agents_dir / "state.json").write_text(json.dumps(old_state), encoding="utf-8")

    loaded = SessionState.load(agents_dir)
    assert loaded.session_id == "legacy-001"
    assert loaded.stop_context is None


def test_safety_stop_context_persisted(tmp_path: Path):
    """Safety stop should persist full stop context to state.json."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="max_tasks",
            threshold_snapshot={"completed": 10, "max_tasks_per_session": 10},
            stop_reason="reached max task cap (10)",
            stopped_at="2026-03-31T00:00:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context is not None
    assert loaded.stop_context.stop_kind == "max_tasks"
    assert loaded.stop_context.threshold_snapshot["completed"] == 10
    assert loaded.stop_context.threshold_snapshot["max_tasks_per_session"] == 10
    assert loaded.stop_context.stop_reason == "reached max task cap (10)"
    assert loaded.stop_context.reflection_signal is None
    assert loaded.stop_context.stopped_at == "2026-03-31T00:00:00+00:00"


def test_consecutive_blocked_stop_context(tmp_path: Path):
    """Consecutive blocked breaker should include count and limit in snapshot."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="consecutive_blocked",
            threshold_snapshot={"consecutive_blocked": 3, "consecutive_block_limit": 2},
            stop_reason="too many blocked",
            stopped_at="2026-03-31T01:00:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context.stop_kind == "consecutive_blocked"
    assert loaded.stop_context.threshold_snapshot["consecutive_blocked"] == 3


def test_stop_signal_stop_context(tmp_path: Path):
    """Manual stop signal should record stop_kind=stop_signal."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="stop_signal",
            stop_reason="manual stop",
            stopped_at="2026-03-31T02:00:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context.stop_kind == "stop_signal"
    assert loaded.stop_context.stop_reason == "manual stop"


def test_vision_drift_stop_context(tmp_path: Path):
    """VISION_DRIFT should persist both reflection_signal and stop context."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    drift_line = "VISION_DRIFT: project deviating from original goals"
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="vision_drift",
            stop_reason=drift_line,
            reflection_signal=drift_line,
            stopped_at="2026-03-31T03:00:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context is not None
    assert loaded.stop_context.stop_kind == "vision_drift"
    assert loaded.stop_context.reflection_signal == drift_line
    assert loaded.stop_context.stop_reason == drift_line


def test_vision_stale_stop_context(tmp_path: Path):
    """VISION_STALE should record the correct stop_kind."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    stale_line = "VISION_STALE: vision document is outdated"
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="vision_stale",
            stop_reason=stale_line,
            reflection_signal=stale_line,
            stopped_at="2026-03-31T03:30:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context.stop_kind == "vision_stale"
    assert loaded.stop_context.reflection_signal == stale_line


def test_safety_stop_preserves_prior_reflection_signal(tmp_path: Path):
    """Safety stop should carry forward the previously recorded reflection_signal."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="vision_drift",
            reflection_signal="VISION_DRIFT: slight drift detected",
            stop_reason="VISION_DRIFT: slight drift detected",
            stopped_at="2026-03-31T04:00:00+00:00",
        ),
    )
    state.save(agents_dir)
    loaded = SessionState.load(agents_dir)
    existing_signal = loaded.stop_context.reflection_signal

    loaded.stop_context = StopContext(
        stop_kind="max_tasks",
        threshold_snapshot={"completed": 10, "max_tasks_per_session": 10},
        stop_reason="task cap reached",
        reflection_signal=existing_signal,
        stopped_at="2026-03-31T04:01:00+00:00",
    )
    loaded.save(agents_dir)

    final = SessionState.load(agents_dir)
    assert final.stop_context.stop_kind == "max_tasks"
    assert final.stop_context.reflection_signal == "VISION_DRIFT: slight drift detected"


def test_stop_context_save_load_roundtrip(tmp_path: Path):
    """Full serialize/deserialize roundtrip for stop_context."""
    agents_dir = tmp_path / ".agents"
    state = SessionState(
        session_id="rt-001",
        mode="auto",
        stop_context=StopContext(
            stop_kind="consecutive_blocked",
            threshold_snapshot={"consecutive_blocked": 2, "consecutive_block_limit": 2},
            stop_reason="circuit breaker tripped",
            reflection_signal="VISION_STALE: stale",
            stopped_at="2026-03-31T05:00:00+00:00",
        ),
    )
    state.save(agents_dir)

    loaded = SessionState.load(agents_dir)
    assert loaded.stop_context is not None
    assert loaded.stop_context.stop_kind == "consecutive_blocked"
    assert loaded.stop_context.reflection_signal == "VISION_STALE: stale"
    assert loaded.stop_context.stopped_at == "2026-03-31T05:00:00+00:00"


def test_stop_context_does_not_affect_progress_display(tmp_path: Path):
    """stop_context should not leak into progress.md display."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)
    state = SessionState(
        session_id="s1",
        mode="auto",
        stop_context=StopContext(
            stop_kind="max_tasks",
            threshold_snapshot={"completed": 5, "max_tasks_per_session": 5},
            stop_reason="cap reached",
            stopped_at="2026-03-31T06:00:00+00:00",
        ),
    )
    update_progress(agents_dir, state)

    content = (agents_dir / "progress.md").read_text(encoding="utf-8")
    assert "stop_kind" not in content
    assert "threshold_snapshot" not in content
    assert "stop_context" not in content


def test_task_record_and_completed_task_roundtrip(tmp_path: Path):
    """TaskRecord / CompletedTask survive save via SessionState."""
    agents_dir = tmp_path / ".agents"
    state = SessionState(
        session_id="s-task",
        mode="idle",
        current_task=TaskRecord(
            id="t1",
            requirement="req",
            state=TaskState.BUILDING,
            iteration=2,
            branch="agent/x",
        ),
        completed=[
            CompletedTask(id="c1", requirement="done", score=4.0, verdict="PASS", iterations=1),
        ],
    )
    state.save(agents_dir)
    loaded = SessionState.load(agents_dir)
    assert loaded.current_task is not None
    assert loaded.current_task.state == TaskState.BUILDING
    assert loaded.completed[0].verdict == "PASS"
