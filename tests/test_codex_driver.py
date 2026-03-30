"""codex.py tests"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from harness.drivers.codex import CodexDriver


def test_compose_prompt_includes_role_instructions_for_known_agent() -> None:
    driver = CodexDriver()

    prompt = driver._compose_prompt(
        "harness-planner",
        "请生成合同",
        readonly=True,
    )

    assert "developer instructions injected by Harness for the current role" in prompt
    assert "You are the Planner role" in prompt
    assert "请生成合同" in prompt
    assert "read-only mode" in prompt


def test_compose_prompt_falls_back_when_role_is_unknown() -> None:
    driver = CodexDriver()

    prompt = driver._compose_prompt(
        "unknown-role",
        "plain prompt",
        readonly=False,
    )

    assert prompt == "plain prompt"


@patch("harness.drivers.codex.subprocess.Popen")
def test_invoke_streams_output_and_reads_final_file(mock_popen: Mock, tmp_path: Path) -> None:
    output_file_path: Path | None = None

    def _fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal output_file_path
        assert "--agent" not in cmd
        assert "--output-last-message" in cmd
        output_file_path = Path(cmd[cmd.index("--output-last-message") + 1])
        output_file_path.write_text("final response", encoding="utf-8")

        proc = MagicMock()
        proc.stdin = io.StringIO()
        proc.stdout = io.StringIO("line 1\nline 2\n")
        proc.returncode = 0
        proc.wait = Mock(return_value=0)
        return proc

    mock_popen.side_effect = _fake_popen

    driver = CodexDriver()
    result = driver.invoke("harness-evaluator", "review this", tmp_path, readonly=True)

    assert result.success is True
    assert result.output == "final response"
    assert result.exit_code == 0
    assert output_file_path is not None
    assert not output_file_path.exists()


@patch("harness.drivers.codex.subprocess.Popen")
def test_invoke_falls_back_to_stdout_when_no_output_file(mock_popen: Mock, tmp_path: Path) -> None:
    def _fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        idx = cmd.index("--output-last-message") + 1
        Path(cmd[idx]).write_text("", encoding="utf-8")

        proc = MagicMock()
        proc.stdin = io.StringIO()
        proc.stdout = io.StringIO("streamed output\n")
        proc.returncode = 0
        proc.wait = Mock(return_value=0)
        return proc

    mock_popen.side_effect = _fake_popen

    driver = CodexDriver()
    result = driver.invoke("harness-planner", "plan this", tmp_path, readonly=True)

    assert result.success is True
    assert "streamed output" in result.output
