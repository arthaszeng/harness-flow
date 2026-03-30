"""Base protocol for agent drivers."""

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
    """Interface for invoking IDE agents."""

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
        """Run an agent with the given prompt.

        on_output: callback per line of subprocess output; when set, the driver should not write stderr directly.
        """
        ...

    def is_available(self) -> bool:
        """Whether the IDE CLI is available."""
        ...

    @property
    def name(self) -> str:
        """Driver name."""
        ...
