"""Tests for harness validate-artifacts CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from harness.cli import app

runner = CliRunner()


@pytest.fixture()
def task_dir(tmp_path: Path) -> Path:
    agents = tmp_path / ".harness-flow" / "tasks" / "task-099"
    agents.mkdir(parents=True)
    return agents


def test_json_output_structure(task_dir: Path) -> None:
    with patch("harness.commands.validate_artifacts.Path.cwd", return_value=task_dir.parent.parent.parent):
        result = runner.invoke(app, ["validate-artifacts", "--task", "task-099", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["task_id"] == "task-099"
    assert "artifacts" in data
    assert "summary" in data
    assert "next_actions" in data


def test_task_not_found(tmp_path: Path) -> None:
    agents = tmp_path / ".harness-flow" / "tasks"
    agents.mkdir(parents=True)
    with patch("harness.commands.validate_artifacts.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["validate-artifacts", "--task", "task-nonexistent", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False


def test_with_plan_only(task_dir: Path) -> None:
    (task_dir / "plan.md").write_text(
        "# Spec\n## System Design Thinking\n### Core Challenge\ntest\n"
        "### Architecture Constraints\ntest\n### Design Pitfalls\ntest\n"
        "## Analysis\ntest\n## Approach\ntest\n## Impact\ntest\n## Risks\ntest\n"
        "---\n# Contract\n## Design Principles\n- [ ] DP1: test\n"
        "## Deliverables\n- [ ] D1: test\n## Acceptance Criteria\ntest\n"
        "## Out of Scope\ntest\n",
        encoding="utf-8",
    )
    with patch("harness.commands.validate_artifacts.Path.cwd", return_value=task_dir.parent.parent.parent):
        result = runner.invoke(app, ["validate-artifacts", "--task", "task-099", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    done = data["summary"]["done"]
    assert "plan" in done
    ready = data["summary"]["ready"]
    assert "build-log" in ready


def test_text_output(task_dir: Path) -> None:
    with patch("harness.commands.validate_artifacts.Path.cwd", return_value=task_dir.parent.parent.parent):
        result = runner.invoke(app, ["validate-artifacts", "--task", "task-099", "--text"])
    assert result.exit_code == 0
    assert "Artifact Report" in result.output
    assert "plan" in result.output
