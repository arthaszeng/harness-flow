"""Tests for the PR CI monitoring module."""

from __future__ import annotations

from pathlib import Path

from harness.core.pr_monitor import FailureCategory, PrMonitor
from harness.integrations.gh_ops import FailedJobLog, PrCheckRun, PrStatusSummary
from harness.integrations.git_ops import GitOperationResult


def _ok_result(**overrides) -> GitOperationResult:
    defaults = {"ok": True, "code": "OK", "stdout": "", "stderr": ""}
    defaults.update(overrides)
    return GitOperationResult(**defaults)


def _fail_result(**overrides) -> GitOperationResult:
    defaults = {"ok": False, "code": "GH_NOT_FOUND", "message": "gh not found"}
    defaults.update(overrides)
    return GitOperationResult(**defaults)


def test_check_status_delegates_to_gh_ops(tmp_path: Path, monkeypatch):
    summary = PrStatusSummary(
        pr_number=42, ci_status="pass", mergeable=True, conflict=False,
        checks=[PrCheckRun(name="CI", status="completed", conclusion="success")],
    )
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_pr_status",
        lambda cwd, **kw: (_ok_result(), summary),
    )
    monitor = PrMonitor.create(tmp_path)
    result, s = monitor.check_status(pr_number=42)
    assert result.ok is True
    assert s is not None
    assert s.ci_status == "pass"


def test_check_status_gh_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_pr_status",
        lambda cwd, **kw: (_fail_result(), None),
    )
    monitor = PrMonitor.create(tmp_path)
    result, s = monitor.check_status(pr_number=1)
    assert result.ok is False
    assert s is None


def test_get_failure_logs_delegates(tmp_path: Path, monkeypatch):
    jobs = [FailedJobLog(name="test", conclusion="failure", log_tail="assert False")]
    monkeypatch.setattr(
        "harness.core.pr_monitor.gh_ci_logs",
        lambda cwd, **kw: (_ok_result(), jobs),
    )
    monitor = PrMonitor.create(tmp_path)
    result, logs = monitor.get_failure_logs(branch="feature")
    assert result.ok is True
    assert len(logs) == 1


def test_diagnose_auto_fixable():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [FailedJobLog(name="lint", conclusion="failure", log_tail="ruff check failed: unused import")]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 1
    assert diagnoses[0].category == FailureCategory.AUTO_FIXABLE


def test_diagnose_infra_issue():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [FailedJobLog(name="build", conclusion="failure", log_tail="rate limit exceeded for API")]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 1
    assert diagnoses[0].category == FailureCategory.INFRA_ISSUE


def test_diagnose_needs_human():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [FailedJobLog(name="deploy", conclusion="failure", log_tail="segmentation fault")]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 1
    assert diagnoses[0].category == FailureCategory.NEEDS_HUMAN


def test_diagnose_import_error():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [FailedJobLog(name="test", conclusion="failure", log_tail="ModuleNotFoundError: No module named 'foo'")]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 1
    assert diagnoses[0].category == FailureCategory.AUTO_FIXABLE


def test_diagnose_test_failure():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [FailedJobLog(name="test", conclusion="failure", log_tail="AssertionError: expected 5 got 3")]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 1
    assert diagnoses[0].category == FailureCategory.AUTO_FIXABLE


def test_diagnose_multiple_jobs():
    monitor = PrMonitor(project_root=Path("/tmp"))
    jobs = [
        FailedJobLog(name="lint", conclusion="failure", log_tail="ruff error"),
        FailedJobLog(name="infra", conclusion="failure", log_tail="503 service unavailable"),
        FailedJobLog(name="unknown", conclusion="failure", log_tail="something unusual"),
    ]
    diagnoses = monitor.diagnose_failures(jobs)
    assert len(diagnoses) == 3
    categories = {d.category for d in diagnoses}
    assert FailureCategory.AUTO_FIXABLE in categories
    assert FailureCategory.INFRA_ISSUE in categories
    assert FailureCategory.NEEDS_HUMAN in categories
