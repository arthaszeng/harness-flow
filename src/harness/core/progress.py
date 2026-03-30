"""进展报告生成器 — 维护 .agents/progress.md"""

from __future__ import annotations

from pathlib import Path

from harness.core.state import CompletedTask, SessionState


def update_progress(agents_dir: Path, state: SessionState) -> None:
    """根据当前 state 重新生成 progress.md"""
    path = agents_dir / "progress.md"
    lines: list[str] = []

    project_name = state.session_id.split("T")[0] if state.session_id else "unknown"
    lines.append(f"# Progress Report\n")
    lines.append(f"## Session {state.session_id}\n")

    # 已完成
    lines.append("### Completed Tasks\n")
    if state.completed:
        lines.append("| # | Task | Score | Iterations | Time |")
        lines.append("|---|------|-------|-----------|------|")
        for i, task in enumerate(state.completed, 1):
            elapsed = _fmt_elapsed(task.elapsed_seconds)
            lines.append(
                f"| {i} | {task.requirement} | {task.score:.1f} ({task.verdict}) "
                f"| {task.iterations} | {elapsed} |"
            )
    else:
        lines.append("(none)\n")

    # 进行中
    lines.append("\n### In Progress\n")
    if state.current_task:
        t = state.current_task
        lines.append(f"- [{t.id}] {t.requirement} — {t.state.value} (iteration {t.iteration})")
    else:
        lines.append("(none)")

    # 阻塞
    lines.append("\n### Blocked\n")
    if state.blocked:
        for task in state.blocked:
            lines.append(f"- [{task.id}] {task.requirement} — score {task.score:.1f}")
    else:
        lines.append("(none)")

    # 统计
    lines.append("\n### Stats\n")
    s = state.stats
    total = s.completed + s.blocked
    lines.append(f"- Completed: {s.completed}/{s.total_tasks} tasks")
    lines.append(f"- Blocked: {s.blocked}")
    lines.append(f"- Average score: {s.avg_score:.1f}")
    lines.append(f"- Total iterations: {s.total_iterations}")
    lines.append(f"- Elapsed: {_fmt_elapsed(s.elapsed_seconds)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt_elapsed(seconds: float) -> str:
    """格式化耗时"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins = seconds / 60
    if mins < 60:
        return f"{mins:.0f}min"
    hours = mins / 60
    return f"{hours:.1f}h"
