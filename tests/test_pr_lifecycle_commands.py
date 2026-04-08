"""Tests for PR lifecycle CLI commands (pr-status, ci-logs)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from harness.cli import app
from harness.integrations.gh_ops import PrCheckRun, PrStatusSummary
from harness.integrations.git_ops import GitOperationResult

runner = CliRunner()


def _ok_result(**overrides) -> GitOperationResult:
    defaults = {"ok": True, "code": "OK", "stdout": "", "stderr": ""}
    defaults.update(overrides)
    return GitOperationResult(**defaults)


def _fail_result(**overrides) -> GitOperationResult:
    defaults = {"ok": False, "code": "GH_NOT_FOUND", "message": "gh not found"}
    defaults.update(overrides)
    return GitOperationResult(**defaults)


def test_pr_status_json(monkeypatch):
    summary = PrStatusSummary(
        pr_number=99,
        ci_status="pass",
        mergeable=True,
        conflict=False,
        checks=[PrCheckRun(name="CI", status="completed", conclusion="success")],
    )
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_pr_status",
        lambda cwd, **kw: (_ok_result(), summary),
    )
    result = runner.invoke(app, ["pr-status", "--pr", "99", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ci_status"] == "pass"
    assert data["mergeable"] is True
    assert data["pr_number"] == 99


def test_pr_status_by_branch(monkeypatch):
    summary = PrStatusSummary(
        pr_number=100,
        ci_status="fail",
        mergeable=False,
        conflict=True,
        checks=[],
    )
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_pr_status",
        lambda cwd, **kw: (_ok_result(), summary),
    )
    result = runner.invoke(app, ["pr-status", "--branch", "feature", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ci_status"] == "fail"
    assert data["conflict"] is True


def test_pr_status_gh_unavailable(monkeypatch):
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_pr_status",
        lambda cwd, **kw: (_fail_result(), None),
    )
    result = runner.invoke(app, ["pr-status", "--pr", "1", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False


def test_pr_status_requires_selector():
    result = runner.invoke(app, ["pr-status"])
    assert result.exit_code != 0


def test_ci_logs_json_empty(monkeypatch):
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_ci_logs",
        lambda cwd, **kw: (_ok_result(), []),
    )
    result = runner.invoke(app, ["ci-logs", "--pr", "5", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["failed_jobs"] == []


def test_ci_logs_gh_unavailable(monkeypatch):
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_ci_logs",
        lambda cwd, **kw: (_fail_result(), []),
    )
    result = runner.invoke(app, ["ci-logs", "--pr", "5", "--json"])
    assert result.exit_code == 1
