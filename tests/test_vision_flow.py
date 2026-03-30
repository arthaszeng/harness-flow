"""vision_flow.py + advisor 相关测试"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from harness.drivers.base import AgentResult
from harness.orchestrator.autonomous import detect_vision_drift
from harness.orchestrator.vision_flow import (
    AdvisorOutput,
    ProjectContext,
    build_advisor_prompt,
    gather_context,
    invoke_advisor,
    parse_advisor_output,
    write_vision,
)


# === gather_context ===


def test_gather_context_reads_existing_files(tmp_path: Path) -> None:
    agents = tmp_path / ".agents"
    agents.mkdir()
    (agents / "vision.md").write_text("# Vision\ngoals here", encoding="utf-8")
    (agents / "reflection.md").write_text("# Reflection\nsome notes", encoding="utf-8")
    (agents / "progress.md").write_text("# Progress\ntask-001 done", encoding="utf-8")

    doc = tmp_path / "doc"
    doc.mkdir()
    (doc / "arch.md").write_text("# Architecture\nlayered", encoding="utf-8")

    ctx = gather_context(tmp_path)

    assert "goals here" in ctx.existing_vision
    assert "some notes" in ctx.reflection
    assert "task-001 done" in ctx.progress
    assert len(ctx.doc_summaries) == 1
    assert "arch.md" in ctx.doc_summaries[0]


def test_gather_context_handles_missing_files(tmp_path: Path) -> None:
    (tmp_path / ".agents").mkdir()
    ctx = gather_context(tmp_path)

    assert ctx.existing_vision == ""
    assert ctx.reflection == ""
    assert ctx.progress == ""
    assert ctx.doc_summaries == []


# === build_advisor_prompt ===


def test_build_advisor_prompt_includes_all_sections() -> None:
    ctx = ProjectContext(
        project_name="myproject",
        existing_vision="old vision content",
        reflection="reflector says update",
        progress="task-001 done",
        doc_summaries=["### README.md\nproject readme"],
        directory_tree="src/\ntests/",
    )

    prompt = build_advisor_prompt(ctx, "我想做回测引擎")

    assert "myproject" in prompt
    assert "我想做回测引擎" in prompt
    assert "old vision content" in prompt
    assert "reflector says update" in prompt
    assert "task-001 done" in prompt
    assert "README.md" in prompt
    assert "src/" in prompt


def test_build_advisor_prompt_skips_empty_sections() -> None:
    ctx = ProjectContext(project_name="test")
    prompt = build_advisor_prompt(ctx, "build something")

    assert "test" in prompt
    assert "build something" in prompt
    assert "现有 Vision" not in prompt
    assert "Reflector 反思" not in prompt


# === parse_advisor_output ===


def test_parse_advisor_output_extracts_vision_only() -> None:
    output = "# Project Vision\n\n## 项目目标\nA good project"
    result = parse_advisor_output(output)

    assert "A good project" in result.vision_content
    assert result.questions == []


def test_parse_advisor_output_splits_questions() -> None:
    output = (
        "# Project Vision\n\n## 项目目标\nA good project\n\n"
        "ADVISOR_QUESTIONS:\n"
        "1. 你想先做哪个功能？\n"
        "2. 有没有不想做的？\n"
    )
    result = parse_advisor_output(output)

    assert "A good project" in result.vision_content
    assert "ADVISOR_QUESTIONS" not in result.vision_content
    assert len(result.questions) == 2
    assert "你想先做哪个功能？" in result.questions[0]
    assert "有没有不想做的？" in result.questions[1]


def test_parse_advisor_output_handles_no_questions_marker() -> None:
    output = "just vision content"
    result = parse_advisor_output(output)
    assert result.vision_content == "just vision content"
    assert result.questions == []


# === invoke_advisor ===


def test_invoke_advisor_returns_parsed_output(tmp_path: Path) -> None:
    mock_driver = MagicMock()
    mock_driver.invoke.return_value = AgentResult(
        success=True,
        output="# Vision\n\n## 项目目标\nExpanded goal",
        exit_code=0,
    )

    ctx = ProjectContext(project_name="test")
    result = invoke_advisor(mock_driver, "harness-advisor", ctx, "做回测", tmp_path)

    assert "Expanded goal" in result.vision_content
    assert result.questions == []
    mock_driver.invoke.assert_called_once()


def test_invoke_advisor_handles_failure(tmp_path: Path) -> None:
    mock_driver = MagicMock()
    mock_driver.invoke.return_value = AgentResult(
        success=False, output="timeout", exit_code=1,
    )

    ctx = ProjectContext(project_name="test")
    result = invoke_advisor(mock_driver, "harness-advisor", ctx, "做回测", tmp_path)

    assert result.vision_content == ""
    assert len(result.questions) == 1


# === write_vision ===


def test_write_vision_creates_file(tmp_path: Path) -> None:
    content = "# Project Vision\n\n## 项目目标\nNew vision"
    size = write_vision(tmp_path, content)

    written = (tmp_path / "vision.md").read_text(encoding="utf-8")
    assert written == content
    assert size == len(content.encode("utf-8"))


def test_write_vision_overwrites_existing(tmp_path: Path) -> None:
    (tmp_path / "vision.md").write_text("old", encoding="utf-8")
    write_vision(tmp_path, "new vision")

    assert (tmp_path / "vision.md").read_text(encoding="utf-8") == "new vision"


# === detect_vision_drift ===


def test_detect_vision_drift_finds_drift() -> None:
    output = (
        "## Vision 对齐度\n"
        "目标完成 60%\n"
        "VISION_DRIFT: 实际方向偏向了数据管道，但 vision 仍侧重回测\n"
    )
    result = detect_vision_drift(output)
    assert result is not None
    assert "VISION_DRIFT" in result
    assert "数据管道" in result


def test_detect_vision_drift_finds_stale() -> None:
    output = "## Vision 对齐度\nVISION_STALE: 所有目标已完成，建议规划下一阶段\n"
    result = detect_vision_drift(output)
    assert result is not None
    assert "VISION_STALE" in result


def test_detect_vision_drift_returns_none_for_normal() -> None:
    output = "## Vision 对齐度\n目标完成 30%，方向一致\n"
    result = detect_vision_drift(output)
    assert result is None
