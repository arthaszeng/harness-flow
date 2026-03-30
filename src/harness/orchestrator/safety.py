"""安全阀 — 熔断、停止信号、方向检测"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness.core.config import AutonomousConfig
from harness.core.state import StateMachine


@dataclass
class SafetyCheck:
    should_stop: bool
    reason: str = ""


def check_safety(
    sm: StateMachine,
    config: AutonomousConfig,
    completed: int,
    consecutive_blocked: int,
) -> SafetyCheck:
    """综合安全检查"""
    # 1. 停止信号
    if sm.stop_requested():
        return SafetyCheck(should_stop=True, reason="收到 harness stop 信号")

    # 2. 任务上限
    if completed >= config.max_tasks_per_session:
        return SafetyCheck(
            should_stop=True,
            reason=f"达到会话任务上限 ({config.max_tasks_per_session})",
        )

    # 3. 连续阻塞熔断
    if consecutive_blocked >= config.consecutive_block_limit:
        return SafetyCheck(
            should_stop=True,
            reason=f"连续 {consecutive_blocked} 个任务阻塞，触发熔断",
        )

    return SafetyCheck(should_stop=False)


def write_stop_signal(agents_dir: Path) -> None:
    """写入停止信号文件"""
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / ".stop").write_text("stop", encoding="utf-8")
