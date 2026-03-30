"""harness auto — 启动自治开发循环"""

from __future__ import annotations

from pathlib import Path

import typer

from harness.core.config import HarnessConfig
from harness.core.state import SessionState, StateMachine
from harness.core.ui import get_ui, init_ui
from harness.drivers.resolver import DriverResolver
from harness.orchestrator.autonomous import run_autonomous


def run_auto(*, resume: bool = False, verbose: bool = False) -> None:
    """启动 Strategist 驱动的自治循环"""
    init_ui(verbose=verbose)
    ui = get_ui()

    project_root = Path.cwd()
    agents_dir = project_root / ".agents"

    if not (agents_dir / "config.toml").exists():
        ui.error("未找到 .agents/config.toml，请先运行 `harness init`")
        raise typer.Exit(1)

    if not (agents_dir / "vision.md").exists():
        ui.error("未找到 .agents/vision.md，请先编辑项目愿景")
        raise typer.Exit(1)

    config = HarnessConfig.load(project_root)
    sm = StateMachine(project_root)

    if not resume:
        incomplete = SessionState.detect_incomplete(agents_dir)
        if incomplete:
            do_resume = typer.confirm(
                f"检测到未完成的会话 ({incomplete.session_id})，是否恢复?",
                default=True,
            )
            if do_resume:
                resume = True
            else:
                ui.info("abandoned previous session, starting fresh")

    resolver = DriverResolver(config)
    avail = resolver.available_drivers
    if not any(avail.values()):
        ui.error("未检测到 Cursor 或 Codex CLI")
        raise typer.Exit(1)

    if not resume:
        sm.start_session("auto")

    sm.clear_stop_signal()

    results = run_autonomous(config, sm, resolver, resume=resume)

    sm.end_session()

    passed = sum(1 for r in results if r.verdict == "PASS")
    blocked = sum(1 for r in results if r.verdict != "PASS")
    ui.info(f"autonomous loop finished: {passed} passed, {blocked} blocked")
