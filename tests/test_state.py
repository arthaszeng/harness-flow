"""state.py 单元测试"""

import json
from pathlib import Path

import pytest

from harness.core.state import (
    SessionState,
    StateMachine,
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
    # 空状态 → 无未完成
    assert SessionState.detect_incomplete(agents_dir) is None

    # 有活跃任务
    from harness.core.state import TaskRecord
    state = SessionState(
        session_id="test",
        mode="run",
        current_task=TaskRecord(id="t1", requirement="test"),
    )
    state.save(agents_dir)
    incomplete = SessionState.detect_incomplete(agents_dir)
    assert incomplete is not None
    assert incomplete.current_task.id == "t1"


def test_state_machine_transitions(tmp_path: Path):
    sm = StateMachine(tmp_path)
    sm.start_session("run")
    sm.start_task("t1", "do something", "agent/test")

    sm.transition(TaskState.PLANNING)
    assert sm.state.current_task.state == TaskState.PLANNING
    assert sm.state.current_task.iteration == 1

    sm.transition(TaskState.CONTRACTED)
    sm.transition(TaskState.BUILDING)
    sm.transition(TaskState.EVALUATING)
    sm.transition(TaskState.DONE)

    sm.complete_task(score=4.0, verdict="PASS")
    assert len(sm.state.completed) == 1
    assert sm.state.stats.completed == 1


def test_invalid_transition(tmp_path: Path):
    sm = StateMachine(tmp_path)
    sm.start_session("run")
    sm.start_task("t1", "test", "agent/test")

    with pytest.raises(ValueError, match="非法转换"):
        sm.transition(TaskState.EVALUATING)  # IDLE → EVALUATING 非法


def test_stop_signal(tmp_path: Path):
    sm = StateMachine(tmp_path)
    sm.start_session("run")  # 确保 .agents 目录存在
    assert not sm.stop_requested()

    (tmp_path / ".agents" / ".stop").write_text("stop", encoding="utf-8")
    assert sm.stop_requested()

    sm.clear_stop_signal()
    assert not sm.stop_requested()
