"""harness git lifecycle helper commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from harness.core.branch_lifecycle import BranchLifecycleManager


def run_git_preflight(*, as_json: bool = False) -> None:
    manager = BranchLifecycleManager.create(Path.cwd())
    result = manager.preflight_repo_state()
    payload = {
        "ok": result.ok,
        "code": result.code,
        "message": result.diagnostic,
        "context": result.context,
    }
    if as_json:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(f"[{result.code}] {result.diagnostic}")
    if not result.ok:
        raise typer.Exit(code=1)


def run_git_prepare_branch(*, task_key: str, short_desc: str = "", as_json: bool = False) -> None:
    manager = BranchLifecycleManager.create(Path.cwd())
    result = manager.prepare_task_branch(task_key, short_desc)
    payload = {
        "ok": result.ok,
        "code": result.code,
        "message": result.diagnostic,
        "context": result.context,
    }
    if as_json:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(f"[{result.code}] {result.diagnostic}")
    if not result.ok:
        raise typer.Exit(code=1)

