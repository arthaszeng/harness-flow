"""索引维护 — 自动更新 .agents/index.md"""

from __future__ import annotations

from pathlib import Path

from harness.core.state import SessionState


def update_index(agents_dir: Path, state: SessionState) -> None:
    """更新 .agents/index.md — 所有任务的快速索引"""
    path = agents_dir / "index.md"
    lines = ["# Task Index\n"]

    # 活跃任务
    if state.current_task:
        t = state.current_task
        lines.append("## Active\n")
        lines.append(f"- **{t.id}**: {t.requirement} [{t.state.value}]\n")

    # 已完成
    if state.completed:
        lines.append("## Completed\n")
        for t in state.completed:
            lines.append(f"- **{t.id}**: {t.requirement} — {t.score:.1f} ({t.verdict})")

    # 阻塞
    if state.blocked:
        lines.append("\n## Blocked\n")
        for t in state.blocked:
            lines.append(f"- **{t.id}**: {t.requirement} — {t.score:.1f}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
