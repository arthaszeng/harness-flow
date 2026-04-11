"""harness barrier — async sidecar barrier management."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from harness.core.barriers import (
    BarrierStatus,
    check_barriers,
    complete_barrier,
    list_barriers,
    register_barrier,
)
from harness.core.workflow_state import resolve_task_dir

app = typer.Typer(help="Barrier management for async sidecar tasks")


def _resolve_task(task: str | None) -> Path:
    agents_dir = Path.cwd() / ".harness-flow"
    task_dir = resolve_task_dir(agents_dir, explicit_task_id=task)
    if task_dir is None:
        typer.echo(json.dumps({"error": "no task directory found"}), err=True)
        raise typer.Exit(1)
    return task_dir


@app.command("register")
def register_cmd(
    task: str = typer.Option("", "--task", "-t", help="Task ID"),
    barrier_id: str = typer.Option(..., "--id", help="Barrier identifier"),
    phase: str = typer.Option("ship", "--phase", "-p", help="Phase: plan|build|ship"),
    required: bool = typer.Option(False, "--required", "-r", help="Required for gate"),
    as_json: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
) -> None:
    """Register a new barrier in pending state."""
    task_dir = _resolve_task(task or None)
    record = register_barrier(task_dir, barrier_id=barrier_id, phase=phase, required=required)
    if as_json:
        typer.echo(json.dumps({"ok": True, "barrier": record.model_dump()}))
    else:
        typer.echo(f"  ✓ barrier '{barrier_id}' registered (phase={phase}, required={required})")


@app.command("complete")
def complete_cmd(
    task: str = typer.Option("", "--task", "-t", help="Task ID"),
    barrier_id: str = typer.Option(..., "--id", help="Barrier identifier"),
    status: str = typer.Option("done", "--status", "-s", help="Status: done|failed|skipped"),
    error: str = typer.Option("", "--error", help="Error message (for failed)"),
    result_ref: str = typer.Option("", "--result-ref", help="Reference to result artifact"),
    as_json: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
) -> None:
    """Complete a barrier with given status (idempotent)."""
    task_dir = _resolve_task(task or None)
    try:
        barrier_status = BarrierStatus(status)
    except ValueError:
        typer.echo(json.dumps({"error": f"invalid status: {status}"}), err=True)
        raise typer.Exit(1)

    record = complete_barrier(
        task_dir,
        barrier_id=barrier_id,
        status=barrier_status,
        error=error or None,
        result_ref=result_ref or None,
    )
    if as_json:
        typer.echo(json.dumps({"ok": True, "barrier": record.model_dump()}))
    else:
        typer.echo(f"  ✓ barrier '{barrier_id}' → {status}")


@app.command("check")
def check_cmd(
    task: str = typer.Option("", "--task", "-t", help="Task ID"),
    phase: str = typer.Option("", "--phase", "-p", help="Filter by phase"),
    required_only: bool = typer.Option(False, "--required-only", help="Only check required barriers"),
    as_json: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
) -> None:
    """Check barrier completion status."""
    task_dir = _resolve_task(task or None)
    result = check_barriers(
        task_dir,
        phase=phase or None,
        required_only=required_only,
    )
    if as_json:
        typer.echo(json.dumps(result.to_dict()))
    else:
        icon = "✓" if result.all_required_done else "✗"
        typer.echo(f"  {icon} barriers: {result.done}/{result.total} done")
        if result.required_not_done:
            typer.echo(f"    required not done: {', '.join(result.required_not_done)}")
    if not result.all_required_done:
        raise typer.Exit(1)


@app.command("list")
def list_cmd(
    task: str = typer.Option("", "--task", "-t", help="Task ID"),
    as_json: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
) -> None:
    """List all barriers for a task."""
    task_dir = _resolve_task(task or None)
    records = list_barriers(task_dir)
    if as_json:
        typer.echo(json.dumps([r.model_dump() for r in records], default=str))
    else:
        if not records:
            typer.echo("  (no barriers)")
        for r in records:
            icon = {"done": "✓", "failed": "✗", "pending": "○", "running": "◔", "skipped": "–"}
            typer.echo(f"  {icon.get(r.status.value, '?')} {r.id} [{r.status.value}] (phase={r.phase})")
