"""CLI handlers for PR lifecycle commands (pr-status, ci-logs)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

import typer

from harness.core.ui import get_ui


def run_pr_status(
    *,
    pr: Optional[int] = None,
    branch: str = "",
    as_json: bool = False,
) -> None:
    """Query CI and merge status of a pull request."""
    from harness.core.pr_monitor import PrMonitor

    ui = get_ui()
    monitor = PrMonitor.create()

    result, summary = monitor.check_status(
        pr_number=pr,
        branch=branch or None,
    )

    if not result.ok:
        payload = {"ok": False, "code": result.code, "message": result.message}
        if as_json:
            typer.echo(json.dumps(payload, ensure_ascii=False))
        else:
            ui.error(f"[{result.code}] {result.message}")
        raise typer.Exit(code=1)

    if summary is None:
        payload = {"ok": False, "code": "NO_SUMMARY", "message": "no status summary available"}
        if as_json:
            typer.echo(json.dumps(payload, ensure_ascii=False))
        else:
            ui.error("No status summary available")
        raise typer.Exit(code=1)

    checks_data = [asdict(c) for c in summary.checks]
    output = {
        "pr_number": summary.pr_number,
        "ci_status": summary.ci_status,
        "mergeable": summary.mergeable,
        "conflict": summary.conflict,
        "checks": checks_data,
    }

    if as_json:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        ui.info(f"PR #{summary.pr_number}: CI={summary.ci_status} mergeable={summary.mergeable} conflict={summary.conflict}")
        for check in summary.checks:
            status_icon = "✓" if check.conclusion == "success" else "✗" if check.conclusion in ("failure", "cancelled") else "…"
            ui.info(f"  {status_icon} {check.name}: {check.conclusion or check.status}")


def run_ci_logs(
    *,
    pr: Optional[int] = None,
    branch: str = "",
    as_json: bool = False,
) -> None:
    """Retrieve logs from failed CI jobs."""
    from harness.core.pr_monitor import PrMonitor

    ui = get_ui()
    monitor = PrMonitor.create()

    result, failed_jobs = monitor.get_failure_logs(
        pr_number=pr,
        branch=branch or None,
    )

    if not result.ok:
        payload = {"ok": False, "code": result.code, "message": result.message}
        if as_json:
            typer.echo(json.dumps(payload, ensure_ascii=False))
        else:
            ui.error(f"[{result.code}] {result.message}")
        raise typer.Exit(code=1)

    jobs_data = [asdict(j) for j in failed_jobs]
    output = {"failed_jobs": jobs_data}

    if as_json:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if not failed_jobs:
            ui.info("No failed jobs found")
        else:
            for job in failed_jobs:
                ui.info(f"✗ {job.name} ({job.conclusion})")
                if job.log_tail:
                    for line in job.log_tail.splitlines()[-10:]:
                        ui.info(f"  {line}")
