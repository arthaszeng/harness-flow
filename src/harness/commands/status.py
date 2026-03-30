"""harness status — Rich 终端面板"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from harness.core.state import SessionState
from harness.core.ui import get_ui


def run_status() -> None:
    """读取 state.json 并渲染 Rich 面板"""
    ui = get_ui()
    console = ui.console

    agents_dir = Path.cwd() / ".agents"
    state = SessionState.load(agents_dir)

    if state.mode == "idle" and not state.completed and not state.blocked:
        ui.info("no active session. run `harness run` or `harness auto` to begin.")
        return

    _render_header(console, state)
    _render_current(console, state)
    _render_completed(console, state)
    _render_stats(console, state)


def _render_header(console, state: SessionState) -> None:
    mode_str = state.mode.upper() if state.mode != "idle" else "IDLE"
    console.print(Panel(
        f"[bold]HARNESS[/bold] — Session {state.session_id or 'N/A'}",
        subtitle=f"{mode_str} mode",
        border_style="cyber.border",
    ))


def _render_current(console, state: SessionState) -> None:
    if not state.current_task:
        return
    t = state.current_task
    console.print(f"\n[cyber.magenta]Current Task:[/] {t.requirement}")
    console.print(f"  State:    {t.state.value}")
    console.print(f"  Iteration: {t.iteration}")
    console.print(f"  Branch:   [cyber.dim]{t.branch}[/]")


def _render_completed(console, state: SessionState) -> None:
    if not state.completed and not state.blocked:
        return

    if state.completed:
        table = Table(title="Completed Tasks", show_lines=False, border_style="cyber.dim")
        table.add_column("#", style="cyber.dim", width=3)
        table.add_column("Task")
        table.add_column("Score", justify="right")
        table.add_column("Verdict")
        table.add_column("Iters", justify="right")

        for i, t in enumerate(state.completed, 1):
            score_style = "cyber.ok" if t.score >= 3.5 else "cyber.warn"
            table.add_row(
                str(i),
                t.requirement,
                f"[{score_style}]{t.score:.1f}[/{score_style}]",
                t.verdict,
                str(t.iterations),
            )
        console.print()
        console.print(table)

    if state.blocked:
        console.print(f"\n[cyber.red]Blocked ({len(state.blocked)}):[/]")
        for t in state.blocked:
            console.print(f"  - {t.requirement} [cyber.dim](score: {t.score:.1f})[/]")


def _render_stats(console, state: SessionState) -> None:
    s = state.stats
    console.print(
        f"\n[cyber.dim]Tasks: {s.completed} done, {s.blocked} blocked | "
        f"Avg: {s.avg_score:.1f} | Iters: {s.total_iterations}[/]",
    )
