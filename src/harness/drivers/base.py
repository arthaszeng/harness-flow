"""Agent 驱动基础协议"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable


@dataclass
class AgentResult:
    success: bool
    output: str
    exit_code: int


@runtime_checkable
class AgentDriver(Protocol):
    """IDE agent 调用接口"""

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        cwd: Path,
        *,
        readonly: bool = False,
        timeout: int = 600,
        on_output: Callable[[str], None] | None = None,
    ) -> AgentResult:
        """调用 agent 执行任务

        on_output: 每行子进程输出的回调。提供时 driver 不直接写 stderr。
        """
        ...

    def is_available(self) -> bool:
        """检测 IDE CLI 是否可用"""
        ...

    @property
    def name(self) -> str:
        """驱动名称"""
        ...
