"""harness stop — 优雅停止"""

from __future__ import annotations

from pathlib import Path

import typer

from harness.orchestrator.safety import write_stop_signal


def run_stop() -> None:
    """写入停止信号，当前任务完成当前阶段后停止"""
    agents_dir = Path.cwd() / ".agents"
    write_stop_signal(agents_dir)
    typer.echo("已发送停止信号。当前任务将在完成当前阶段后停止。")
    typer.echo("信号文件: .agents/.stop")
