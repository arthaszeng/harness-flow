"""Tests for the unified gh CLI wrapper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from harness.integrations.gh_ops import (
    _parse_log_output,
    gh_ci_logs,
    gh_pr_status,
    run_gh_json,
    run_gh_result,
)


def test_run_gh_result_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, "ok", ""),
    )
    result = run_gh_result(["version"], tmp_path)
    assert result.ok is True
    assert result.code == "OK"
    assert result.stdout == "ok"


def test_run_gh_result_nonzero_exit(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, "", "error msg"),
    )
    result = run_gh_result(["pr", "view"], tmp_path, code_on_error="CUSTOM_CODE")
    assert result.ok is False
    assert result.code == "CUSTOM_CODE"


def test_run_gh_result_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("gh not found")),
    )
    result = run_gh_result(["version"], tmp_path)
    assert result.ok is False
    assert result.code == "GH_NOT_FOUND"


def test_run_gh_result_timeout(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("gh", 10)),
    )
    result = run_gh_result(["pr", "view"], tmp_path, timeout=10)
    assert result.ok is False
    assert result.code == "GH_TIMEOUT"


def test_run_gh_result_os_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("permission denied")),
    )
    result = run_gh_result(["version"], tmp_path)
    assert result.ok is False
    assert result.code == "GH_IO_ERROR"


def test_run_gh_json_success(tmp_path: Path, monkeypatch):
    data = {"number": 42, "state": "OPEN"}
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(data), ""),
    )
    result, parsed = run_gh_json(["pr", "view", "--json", "number"], tmp_path)
    assert result.ok is True
    assert parsed == data


def test_run_gh_json_parse_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, "not json", ""),
    )
    result, parsed = run_gh_json(["pr", "view"], tmp_path)
    assert result.ok is False
    assert result.code == "GH_JSON_PARSE_FAILED"
    assert parsed is None


def test_gh_pr_status_pass(tmp_path: Path, monkeypatch):
    payload = {
        "number": 10,
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "CI", "status": "completed", "conclusion": "SUCCESS", "workflowName": "CI"},
        ],
    }
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
    )
    result, summary = gh_pr_status(tmp_path, pr_number=10)
    assert result.ok is True
    assert summary is not None
    assert summary.ci_status == "pass"
    assert summary.mergeable is True
    assert summary.conflict is False
    assert len(summary.checks) == 1


def test_gh_pr_status_fail(tmp_path: Path, monkeypatch):
    payload = {
        "number": 11,
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "CI", "status": "completed", "conclusion": "FAILURE"},
            {"name": "Lint", "status": "completed", "conclusion": "SUCCESS"},
        ],
    }
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
    )
    result, summary = gh_pr_status(tmp_path, pr_number=11)
    assert result.ok is True
    assert summary is not None
    assert summary.ci_status == "fail"


def test_gh_pr_status_conflict(tmp_path: Path, monkeypatch):
    payload = {
        "number": 12,
        "state": "OPEN",
        "mergeable": "CONFLICTING",
        "statusCheckRollup": [],
    }
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
    )
    result, summary = gh_pr_status(tmp_path, pr_number=12)
    assert result.ok is True
    assert summary is not None
    assert summary.conflict is True
    assert summary.ci_status == "pending"


def test_gh_pr_status_requires_selector(tmp_path: Path):
    result, summary = gh_pr_status(tmp_path)
    assert result.ok is False
    assert result.code == "PR_SELECTOR_REQUIRED"
    assert summary is None


def test_parse_log_output_basic():
    raw = "job1\tstep1\tline 1\njob1\tstep2\tline 2\njob2\tstep1\tother line"
    jobs = _parse_log_output(raw, max_lines=10)
    assert len(jobs) == 2
    assert jobs[0].name == "job1"
    assert "line 1" in jobs[0].log_tail
    assert jobs[1].name == "job2"


def test_parse_log_output_truncates():
    lines = [f"job1\tstep\tline {i}" for i in range(50)]
    raw = "\n".join(lines)
    jobs = _parse_log_output(raw, max_lines=10)
    assert len(jobs) == 1
    assert jobs[0].log_tail.count("\n") == 9  # 10 lines, 9 newlines


def test_gh_ci_logs_no_failed_runs(tmp_path: Path, monkeypatch):
    runs = [{"databaseId": 1, "conclusion": "success", "status": "completed", "headBranch": "main"}]
    monkeypatch.setattr(
        "harness.integrations.gh_ops.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(runs), ""),
    )
    result, jobs = gh_ci_logs(tmp_path, branch="main")
    assert result.ok is True
    assert result.code == "NO_FAILED_RUNS"
    assert jobs == []
