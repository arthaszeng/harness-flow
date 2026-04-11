"""harness ship-prepare — combined pre-computation for ship phase.

Runs diff-stat + escalation-score + review metadata in one call,
designed to execute while CI runs in background.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from harness.core.config import HarnessConfig
from harness.core.diff_collect import collect_diff_data, get_trust_adjustment
from harness.core.escalation import compute_ship_escalation


def run_ship_prepare(*, task: str | None = None, as_json: bool = True) -> None:
    """Pre-compute ship phase metadata (diff + escalation + review hints)."""
    from harness.commands.diff_stat import classify_file
    from harness.core.workflow_state import resolve_task_dir

    cwd = Path.cwd()
    try:
        cfg = HarnessConfig.load(cwd)
    except Exception:
        cfg = HarnessConfig()

    diff_data = collect_diff_data(cwd=cwd, trunk=cfg.workflow.trunk_branch)
    files = diff_data["files"]
    additions = diff_data["additions"]
    deletions = diff_data["deletions"]
    commit_count = diff_data["commit_count"]

    if not files:
        from harness.integrations.git_ops import run_git

        probe = run_git(["diff", "--name-only", f"origin/{cfg.workflow.trunk_branch}..HEAD"], cwd, timeout=10)
        if probe.returncode != 0:
            err_msg = probe.stderr.strip() or f"git diff failed (exit {probe.returncode})"
            if as_json:
                typer.echo(json.dumps({"error": err_msg}))
            raise typer.Exit(1)

    categories: dict[str, list[str]] = {"code": [], "test": [], "doc": [], "other": []}
    for f in files:
        categories[classify_file(f)].append(f)

    trust_adj = get_trust_adjustment(cwd=cwd)

    escalation = compute_ship_escalation(
        changed_files=files,
        total_additions=additions,
        total_deletions=deletions,
        commit_count=commit_count,
        trust_adjustment=trust_adj,
        gate_full_review_min=cfg.native.gate_full_review_min,
        gate_summary_confirm_min=cfg.native.gate_summary_confirm_min,
    )

    agents_dir = cwd / ".harness-flow"
    task_dir = resolve_task_dir(agents_dir, explicit_task_id=task)

    output = {
        "diff_stat": {
            "total_files": len(files),
            "code_files": len(categories["code"]),
            "test_files": len(categories["test"]),
            "doc_files": len(categories["doc"]),
            "additions": additions,
            "deletions": deletions,
        },
        "escalation": escalation.to_dict(),
        "review_dispatch": {
            "level": escalation.level.value,
            "roles": _roles_for_level(escalation.level.value),
        },
        "task_dir": str(task_dir) if task_dir else None,
    }

    if as_json:
        typer.echo(json.dumps(output))
    else:
        typer.echo(f"Ship Prepare: {escalation.level.value} review ({len(files)} files, +{additions}/-{deletions})")


def _roles_for_level(level: str) -> list[str]:
    """Return role list based on escalation level."""
    if level == "FULL":
        return ["architect", "product_owner", "engineer", "qa", "project_manager"]
    if level == "LITE":
        return ["engineer", "qa"]
    return []
