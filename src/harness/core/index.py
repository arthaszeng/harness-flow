"""Index maintenance — keep .agents/index.md up to date."""

from __future__ import annotations

from pathlib import Path

from harness.core.state import SessionState


def update_index(agents_dir: Path, state: SessionState) -> None:
    """Rewrite .agents/index.md as a quick index of all tasks."""
    path = agents_dir / "index.md"
    lines = ["# Task Index\n"]

    # Active task
    if state.current_task:
        t = state.current_task
        lines.append("## Active\n")
        lines.append(f"- **{t.id}**: {t.requirement} [{t.state.value}]\n")

    # Completed
    if state.completed:
        lines.append("## Completed\n")
        for t in state.completed:
            lines.append(f"- **{t.id}**: {t.requirement} — {t.score:.1f} ({t.verdict})")

    # Blocked
    if state.blocked:
        lines.append("\n## Blocked\n")
        for t in state.blocked:
            lines.append(f"- **{t.id}**: {t.requirement} — {t.score:.1f}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
