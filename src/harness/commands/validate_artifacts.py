"""harness validate-artifacts — Unified artifact status report for a task."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from harness.core.artifact_graph import compute_artifact_report
from harness.core.workflow_state import resolve_task_dir


def run_validate_artifacts(
    *,
    task: str | None = None,
    as_json: bool = True,
) -> None:
    """Compute and display artifact status for a task directory."""
    agents_dir = Path.cwd() / ".harness-flow"
    task_dir = resolve_task_dir(agents_dir, explicit_task_id=task)

    if task_dir is None:
        result = {"ok": False, "error": "no task directory found"}
        if as_json:
            typer.echo(json.dumps(result))
        else:
            typer.echo("Error: no task directory found")
        raise typer.Exit(1)

    report = compute_artifact_report(task_dir)
    report_dict = report.to_dict()
    report_dict["ok"] = True

    if as_json:
        typer.echo(json.dumps(report_dict, indent=2))
    else:
        _render_text(report)


def _render_text(report) -> None:
    """Simple text rendering of artifact report."""
    typer.echo(f"\nArtifact Report — {report.task_id}\n")

    status_icons = {
        "done": "✓",
        "ready": "→",
        "blocked": "○",
        "missing": "·",
        "invalid": "✗",
    }

    for a in report.artifacts:
        icon = status_icons.get(a.status.value, "?")
        line = f"  {icon} {a.id}: {a.status.value}"
        if a.file_path:
            line += f"  ({a.file_path})"
        typer.echo(line)
        if a.validation_errors:
            for err in a.validation_errors:
                typer.echo(f"      ✗ {err}")

    if report.next_actions:
        typer.echo("\nNext actions:")
        for action in report.next_actions:
            typer.echo(f"  → {action}")
    typer.echo()
