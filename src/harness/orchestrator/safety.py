"""Safety valve — circuit breaker, stop signal, caps."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness.core.config import AutonomousConfig
from harness.core.state import StateMachine
from harness.i18n import t


@dataclass
class SafetyCheck:
    should_stop: bool
    reason: str = ""
    stop_kind: str = ""
    threshold_snapshot: dict = field(default_factory=dict)


def check_safety(
    sm: StateMachine,
    config: AutonomousConfig,
    completed: int,
    consecutive_blocked: int,
) -> SafetyCheck:
    """Run combined safety checks."""
    # 1. Stop signal
    if sm.stop_requested():
        return SafetyCheck(
            should_stop=True,
            reason=t("safety.stop_signal"),
            stop_kind="stop_signal",
        )

    # 2. Task cap
    if completed >= config.max_tasks_per_session:
        return SafetyCheck(
            should_stop=True,
            reason=t("safety.max_tasks", limit=config.max_tasks_per_session),
            stop_kind="max_tasks",
            threshold_snapshot={
                "completed": completed,
                "max_tasks_per_session": config.max_tasks_per_session,
            },
        )

    # 3. Consecutive blocked circuit breaker
    if consecutive_blocked >= config.consecutive_block_limit:
        return SafetyCheck(
            should_stop=True,
            reason=t("safety.consecutive_blocked", count=consecutive_blocked),
            stop_kind="consecutive_blocked",
            threshold_snapshot={
                "consecutive_blocked": consecutive_blocked,
                "consecutive_block_limit": config.consecutive_block_limit,
            },
        )

    return SafetyCheck(should_stop=False)


def write_stop_signal(agents_dir: Path) -> None:
    """Write the stop signal file."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / ".stop").write_text("stop", encoding="utf-8")
