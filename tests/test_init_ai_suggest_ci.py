"""init._ai_suggest_ci — advisor 路由下 resolve_model 与 driver.invoke(model=...) 透传。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from harness.commands.init import _ai_suggest_ci
from harness.core.scanner import ProjectScan
from harness.drivers.base import AgentResult
from harness.drivers.codex import CodexDriver
from harness.drivers.resolver import DriverResolver


def _write_agents_config(tmp_path: Path, content: str) -> None:
    agents = tmp_path / ".agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "config.toml").write_text(content, encoding="utf-8")


@patch("harness.commands.init.typer")
@patch.object(DriverResolver, "_run_probes", return_value=(False, True))
def test_ai_suggest_ci_loaded_config_models_used_for_advisor(
    _mock_probes, mock_typer, tmp_path: Path,
):
    """真实 HarnessConfig.load 链路：`[models]` 级联结果参与 resolve_model(advisor) 并传入 invoke。"""
    mock_typer.echo = MagicMock()
    mock_typer.confirm = MagicMock(return_value=True)

    _write_agents_config(
        tmp_path,
        '\n'.join(
            [
                '[drivers]',
                'default = "codex"',
                '',
                '[drivers.roles]',
                'advisor = "codex"',
                '',
                '[models]',
                'default = ""',
                '',
                '[models.role_overrides]',
                'advisor = "gpt-advisor-from-toml"',
                '',
            ],
        ),
    )

    scan = ProjectScan()
    with patch.object(CodexDriver, "invoke") as mock_invoke:
        mock_invoke.return_value = AgentResult(
            success=True, output="pytest -q\n", exit_code=0,
        )
        out = _ai_suggest_ci(tmp_path, {"codex": True}, scan, "codex", {})

        mock_invoke.assert_called_once()
        assert mock_invoke.call_args.kwargs["model"] == "gpt-advisor-from-toml"
        assert out == "pytest -q"


@patch("harness.commands.init.typer")
@patch.object(DriverResolver, "_run_probes", return_value=(False, True))
def test_ai_suggest_ci_wizard_roles_overlay_keeps_models_cascade(
    _mock_probes, mock_typer, tmp_path: Path,
):
    """向导传入的 roles 仅覆盖路由，不重建配置，[models] 仍来自 load。"""
    mock_typer.echo = MagicMock()
    mock_typer.confirm = MagicMock(return_value=True)

    _write_agents_config(
        tmp_path,
        '\n'.join(
            [
                '[drivers]',
                'default = "auto"',
                '',
                '[models]',
                'default = ""',
                '',
                '[models.driver_defaults]',
                'codex = "o3-default"',
                '',
            ],
        ),
    )

    scan = ProjectScan()
    with patch.object(CodexDriver, "invoke") as mock_invoke:
        mock_invoke.return_value = AgentResult(
            success=True, output="make test\n", exit_code=0,
        )
        out = _ai_suggest_ci(
            tmp_path, {"codex": True}, scan, "codex", {"advisor": "codex"},
        )

        mock_invoke.assert_called_once()
        assert mock_invoke.call_args.kwargs["model"] == "o3-default"
        assert out == "make test"


@patch("harness.commands.init.typer")
@patch.object(DriverResolver, "_run_probes", return_value=(False, True))
def test_ai_suggest_ci_empty_advisor_model_passes_empty_string_to_invoke(
    _mock_probes, mock_typer, tmp_path: Path,
):
    """空模型保持不写死非空 --model，invoke 收到空字符串由 driver 按 IDE 默认处理。"""
    mock_typer.echo = MagicMock()
    mock_typer.confirm = MagicMock(return_value=True)

    _write_agents_config(
        tmp_path,
        '\n'.join(
            [
                '[drivers]',
                'default = "codex"',
                '',
                '[drivers.roles]',
                'advisor = "codex"',
                '',
                '[models]',
                'default = ""',
                '',
            ],
        ),
    )

    scan = ProjectScan()
    with patch.object(CodexDriver, "invoke") as mock_invoke:
        mock_invoke.return_value = AgentResult(
            success=True, output="make test\n", exit_code=0,
        )
        out = _ai_suggest_ci(
            tmp_path, {"codex": True}, scan, "codex", {"advisor": "codex"},
        )

        mock_invoke.assert_called_once()
        assert mock_invoke.call_args.kwargs["model"] == ""
        assert out == "make test"
