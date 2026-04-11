"""Shared diff data and trust adjustment collection for ship-phase commands.

Eliminates duplication between escalation CLI and ship-prepare by providing
a single source of truth for diff statistics and trust engine integration.
"""

from __future__ import annotations

import re
from pathlib import Path


def collect_diff_data(*, cwd: Path | None = None, trunk: str = "main") -> dict:
    """Collect diff statistics from git for ship escalation.

    Returns ``{"files": [...], "additions": int, "deletions": int, "commit_count": int}``.
    """
    from harness.integrations.git_ops import run_git

    if cwd is None:
        cwd = Path.cwd()

    diff_range = f"origin/{trunk}..HEAD"

    result = run_git(["diff", "--name-only", diff_range], cwd, timeout=10)
    files = (
        [f for f in (result.stdout or "").strip().splitlines() if f]
        if result.returncode == 0
        else []
    )

    stat_result = run_git(["diff", "--shortstat", diff_range], cwd, timeout=10)
    additions, deletions = 0, 0
    if stat_result.returncode == 0:
        stat_line = (stat_result.stdout or "").strip()
        add_m = re.search(r"(\d+)\s+insertion", stat_line)
        del_m = re.search(r"(\d+)\s+deletion", stat_line)
        if add_m:
            additions = int(add_m.group(1))
        if del_m:
            deletions = int(del_m.group(1))

    log_result = run_git(["rev-list", "--count", diff_range], cwd, timeout=10)
    commit_count = 1
    if log_result.returncode == 0:
        try:
            commit_count = int(log_result.stdout.strip())
        except ValueError:
            pass

    return {
        "files": files,
        "additions": additions,
        "deletions": deletions,
        "commit_count": commit_count,
    }


def get_trust_adjustment(*, cwd: Path | None = None) -> int:
    """Best-effort trust adjustment from calibration data. Returns 0 on any failure."""
    try:
        from harness.core.review_calibration import (
            collect_outcomes,
            generate_calibration_report,
        )
        from harness.core.trust_engine import TrustConfig, compute_trust_profile

        agents_dir = (cwd or Path.cwd()) / ".harness-flow"
        outcomes = collect_outcomes(agents_dir)
        if not outcomes:
            return 0
        report = generate_calibration_report(outcomes)
        profile = compute_trust_profile(report, outcomes, config=TrustConfig())
        return profile.escalation_adjustment
    except Exception:
        return 0
