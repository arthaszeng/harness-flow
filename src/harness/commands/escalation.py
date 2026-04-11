"""harness escalation-score — deterministic escalation score computation."""

from __future__ import annotations

import json
from typing import Optional

import typer

from harness.core.config import HarnessConfig
from harness.core.diff_collect import collect_diff_data, get_trust_adjustment
from harness.core.escalation import (
    compute_plan_escalation,
    compute_ship_escalation,
)

app = typer.Typer(help="Escalation score computation")


@app.command("compute")
def compute_cmd(
    phase: str = typer.Option(
        ..., "--phase", "-p", help="Phase: plan or ship",
    ),
    as_json: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
    deliverables: int = typer.Option(0, "--deliverables", help="[plan] Number of deliverables"),
    estimated_files: int = typer.Option(0, "--estimated-files", help="[plan] Estimated files"),
    security: bool = typer.Option(False, "--security", help="[plan] Security change"),
    schema: bool = typer.Option(False, "--schema", help="[plan] Schema change"),
    api: bool = typer.Option(False, "--api", help="[plan] API surface change"),
    review_score: Optional[float] = typer.Option(None, "--review-score", help="[plan] Plan review score"),
    new_feature: bool = typer.Option(True, "--new-feature/--no-new-feature", help="[plan] Is new feature"),
    depth: str = typer.Option("low", "--depth", help="[plan] Interaction depth: low|medium|high"),
) -> None:
    """Compute escalation score for plan or ship phase."""
    trust_adj = get_trust_adjustment()

    if phase == "plan":
        result = compute_plan_escalation(
            deliverable_count=deliverables,
            estimated_files=estimated_files,
            has_security_change=security,
            has_schema_change=schema,
            has_api_change=api,
            plan_review_score=review_score,
            is_new_feature=new_feature,
            interaction_depth=depth,  # type: ignore[arg-type]
            trust_adjustment=trust_adj,
        )
    elif phase == "ship":
        try:
            cfg = HarnessConfig.load()
        except Exception:
            cfg = HarnessConfig()
        diff_data = collect_diff_data(trunk=cfg.workflow.trunk_branch)
        result = compute_ship_escalation(
            changed_files=diff_data["files"],
            total_additions=diff_data["additions"],
            total_deletions=diff_data["deletions"],
            commit_count=diff_data["commit_count"],
            trust_adjustment=trust_adj,
            gate_full_review_min=cfg.native.gate_full_review_min,
            gate_summary_confirm_min=cfg.native.gate_summary_confirm_min,
        )
    else:
        if as_json:
            typer.echo(json.dumps({"error": f"unknown phase: {phase}"}))
        else:
            typer.echo(f"Error: unknown phase '{phase}'", err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(result.to_dict()))
    else:
        typer.echo(f"Escalation: {result.level.value} (score={result.score})")
        for s in result.signals:
            if s.triggered:
                typer.echo(f"  +{s.points} {s.name}: {s.detail}")
