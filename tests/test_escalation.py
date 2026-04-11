"""Tests for harness.core.escalation — deterministic escalation scoring."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from harness.cli import app
from harness.core.escalation import (
    EscalationLevel,
    compute_plan_escalation,
    compute_ship_escalation,
)

runner = CliRunner()


class TestPlanEscalation:
    def test_small_task_fast(self):
        result = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            is_new_feature=False,
        )
        assert result.level == EscalationLevel.FAST
        assert result.score < 3

    def test_large_task_full(self):
        result = compute_plan_escalation(
            deliverable_count=8,
            estimated_files=40,
            has_api_change=True,
            is_new_feature=True,
        )
        assert result.level == EscalationLevel.FULL
        assert result.score >= 5

    def test_security_change_adds_3(self):
        base = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            has_security_change=False,
        )
        sec = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            has_security_change=True,
        )
        assert sec.raw_score == base.raw_score + 3

    def test_schema_change_adds_3(self):
        base = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            has_schema_change=False,
        )
        schema = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            has_schema_change=True,
        )
        assert schema.raw_score == base.raw_score + 3

    def test_low_review_score_adds_2(self):
        result = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            plan_review_score=5.0,
        )
        sig = next(s for s in result.signals if s.name == "low_review_score")
        assert sig.triggered is True
        assert sig.points == 2

    def test_high_review_score_no_penalty(self):
        result = compute_plan_escalation(
            deliverable_count=2,
            estimated_files=3,
            plan_review_score=8.0,
        )
        sig = next(s for s in result.signals if s.name == "low_review_score")
        assert sig.triggered is False

    def test_interaction_depth_high_reduces(self):
        result = compute_plan_escalation(
            deliverable_count=8,
            estimated_files=15,
            interaction_depth="high",
        )
        sig = next(s for s in result.signals if s.name == "interaction_depth")
        assert sig.points == -2

    def test_trust_adjustment_applied(self):
        base = compute_plan_escalation(
            deliverable_count=3,
            estimated_files=5,
            trust_adjustment=0,
        )
        adjusted = compute_plan_escalation(
            deliverable_count=3,
            estimated_files=5,
            trust_adjustment=-2,
        )
        assert adjusted.score == max(0, base.score - 2)
        assert adjusted.trust_adjustment == -2

    def test_score_never_negative(self):
        result = compute_plan_escalation(
            deliverable_count=1,
            estimated_files=1,
            is_new_feature=False,
            trust_adjustment=-10,
        )
        assert result.score >= 0

    def test_to_dict_json_serializable(self):
        result = compute_plan_escalation(
            deliverable_count=5,
            estimated_files=10,
        )
        d = result.to_dict()
        json_str = json.dumps(d)
        assert "score" in json_str
        assert "level" in json_str
        assert "signals" in json_str


class TestShipEscalation:
    def test_small_change_fast(self):
        result = compute_ship_escalation(
            changed_files=["src/main.py"],
            total_additions=10,
            total_deletions=5,
        )
        assert result.level == EscalationLevel.FAST

    def test_large_change_full(self):
        files = [f"src/file{i}.py" for i in range(15)]
        files.extend(["src/auth/login.py", "src/api/routes.py"])
        result = compute_ship_escalation(
            changed_files=files,
            total_additions=300,
            total_deletions=250,
            commit_count=8,
        )
        assert result.level == EscalationLevel.FULL

    def test_risk_dirs_detected(self):
        result = compute_ship_escalation(
            changed_files=["src/auth/login.py", "src/security/crypto.py"],
        )
        sig = next(s for s in result.signals if s.name == "risk_directories")
        assert sig.triggered is True
        assert sig.points > 0

    def test_api_surface_detected(self):
        result = compute_ship_escalation(
            changed_files=["src/api/routes.py", "src/commands/new.py"],
        )
        sig = next(s for s in result.signals if s.name == "api_surface")
        assert sig.triggered is True

    def test_custom_thresholds(self):
        result = compute_ship_escalation(
            changed_files=["a.py", "b.py"],
            gate_full_review_min=2,
            gate_summary_confirm_min=1,
        )
        assert result.level in (EscalationLevel.FAST, EscalationLevel.LITE, EscalationLevel.FULL)

    def test_to_dict_roundtrip(self):
        result = compute_ship_escalation(changed_files=["a.py"])
        d = result.to_dict()
        assert isinstance(d["score"], int)
        assert d["level"] in ("FAST", "LITE", "FULL")


class TestEscalationCLI:
    """CLI-layer tests for escalation-score command."""

    def test_plan_json_output(self):
        result = runner.invoke(app, [
            "escalation-score", "compute",
            "--phase", "plan",
            "--deliverables", "3",
            "--estimated-files", "5",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "score" in data
        assert "level" in data
        assert "signals" in data

    def test_ship_json_output(self):
        mock_result = type("R", (), {"returncode": 0, "stdout": "a.py\nb.py\n", "stderr": ""})()
        stat_result = type("R", (), {"returncode": 0, "stdout": " 2 files changed, 10 insertions(+), 5 deletions(-)\n", "stderr": ""})()
        log_result = type("R", (), {"returncode": 0, "stdout": "2\n", "stderr": ""})()

        def mock_run(cmd, *a, **kw):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "--name-only" in cmd_str:
                return mock_result
            if "--stat" in cmd_str:
                return stat_result
            if "rev-list" in cmd_str:
                return log_result
            return mock_result

        with patch("harness.integrations.git_ops.run_git", side_effect=mock_run):
            result = runner.invoke(app, [
                "escalation-score", "compute",
                "--phase", "ship",
                "--json",
            ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "score" in data
        assert "level" in data
        assert "signals" in data

    def test_unknown_phase_error(self):
        result = runner.invoke(app, [
            "escalation-score", "compute",
            "--phase", "banana",
            "--json",
        ])
        assert result.exit_code == 1

    def test_json_schema_snapshot(self):
        """Pin the escalation output schema keys."""
        result = runner.invoke(app, [
            "escalation-score", "compute",
            "--phase", "plan",
            "--deliverables", "5",
            "--estimated-files", "10",
            "--json",
        ])
        data = json.loads(result.stdout)
        expected_keys = {"score", "level", "raw_score", "trust_adjustment", "signals"}
        assert set(data.keys()) == expected_keys
        assert isinstance(data["signals"], list)
        if data["signals"]:
            sig_keys = {"name", "triggered", "points", "detail"}
            assert set(data["signals"][0].keys()) == sig_keys
