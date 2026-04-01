"""Tests for harness init command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jinja2
import pytest
import typer

from harness.commands.init import (
    KNOWN_MODELS,
    _detect_cursor_model,
    _load_template,
    _prompt_choice,
    _step_ci_command,
    _step_evaluator_model,
    _step_language,
    _step_memverse,
    _update_gitignore,
    run_init,
    validate_model_name,
)
from harness.core.scanner import ProjectScan
from harness.i18n import set_lang


class TestLoadTemplate:
    def test_loads_known_template(self):
        tmpl = _load_template("config.toml.j2")
        assert isinstance(tmpl, jinja2.Template)
        src = tmpl.render(project_name="x", description="", lang="en", ci_command="make test")
        assert 'name = "x"' in src
        assert "make test" in src

    def test_nonexistent_template_raises(self):
        with pytest.raises(FileNotFoundError):
            _load_template("does-not-exist-xyz.j2")


class TestPromptChoice:
    def test_valid_input_returns_one_based_index(self):
        with patch("harness.commands.init.typer.prompt", return_value="2"):
            with patch("harness.commands.init.typer.echo"):
                assert _prompt_choice("pick", 5, default=1) == 2

    def test_invalid_input_loops_until_valid(self):
        with patch(
            "harness.commands.init.typer.prompt",
            side_effect=["99", "0", "nan", "3"],
        ):
            mock_echo = MagicMock()
            with patch("harness.commands.init.typer.echo", mock_echo):
                assert _prompt_choice("pick", 3, default=1) == 3
        assert mock_echo.call_count == 3


class TestStepLanguage:
    def test_choice_1_returns_en(self):
        with patch("harness.commands.init.typer.echo"):
            with patch("harness.commands.init.typer.prompt", return_value="1"):
                assert _step_language() == "en"

    def test_choice_2_returns_zh(self):
        with patch("harness.commands.init.typer.echo"):
            with patch("harness.commands.init.typer.prompt", return_value="2"):
                assert _step_language() == "zh"


class TestStepCiCommand:
    def test_ci_override_returns_directly(self, tmp_path):
        assert _step_ci_command(tmp_path, ci_override="npm test") == "npm test"

    def test_with_suggestions_selects_command(self, tmp_path):
        scan = ProjectScan(
            suggested_commands=[
                ("pytest -q", "pytest"),
                ("make ci", "makefile"),
            ],
        )
        with patch("harness.commands.init.scan_project", return_value=scan):
            with patch("harness.commands.init.format_scan_report", return_value=[]):
                with patch("harness.commands.init.typer.echo"):
                    with patch(
                        "harness.commands.init.typer.prompt",
                        return_value="1",
                    ):
                        assert _step_ci_command(tmp_path) == "pytest -q"

    def test_with_suggestions_custom_index_prompts(self, tmp_path):
        scan = ProjectScan(suggested_commands=[("a", "d")])
        with patch("harness.commands.init.scan_project", return_value=scan):
            with patch("harness.commands.init.format_scan_report", return_value=[]):
                with patch("harness.commands.init.typer.echo"):
                    with patch(
                        "harness.commands.init.typer.prompt",
                        side_effect=["2", "my custom ci"],
                    ):
                        assert _step_ci_command(tmp_path) == "my custom ci"

    def test_no_suggestions_custom_flow(self, tmp_path):
        scan = ProjectScan(suggested_commands=[])
        with patch("harness.commands.init.scan_project", return_value=scan):
            with patch("harness.commands.init.format_scan_report", return_value=[]):
                with patch("harness.commands.init.typer.echo"):
                    with patch(
                        "harness.commands.init.typer.prompt",
                        side_effect=["1", "cargo test"],
                    ):
                        assert _step_ci_command(tmp_path) == "cargo test"

    def test_no_suggestions_skip_returns_empty(self, tmp_path):
        scan = ProjectScan(suggested_commands=[])
        with patch("harness.commands.init.scan_project", return_value=scan):
            with patch("harness.commands.init.format_scan_report", return_value=[]):
                with patch("harness.commands.init.typer.echo"):
                    with patch(
                        "harness.commands.init.typer.prompt",
                        return_value="2",
                    ):
                        assert _step_ci_command(tmp_path) == ""


class TestStepMemverse:
    def test_disable_returns_disabled(self, tmp_path):
        with patch("harness.commands.init.typer.echo"):
            with patch("harness.commands.init.typer.prompt", return_value="2"):
                assert _step_memverse(tmp_path) == (False, "")

    def test_enable_returns_domain(self, tmp_path):
        with patch("harness.commands.init.typer.echo"):
            with patch(
                "harness.commands.init.typer.prompt",
                side_effect=["1", "my-domain"],
            ):
                assert _step_memverse(tmp_path) == (True, "my-domain")


class TestValidateModelName:
    def test_inherit_is_valid(self):
        assert validate_model_name("inherit") is True

    def test_simple_model_name(self):
        assert validate_model_name("gpt-4.1") is True

    def test_complex_model_name(self):
        assert validate_model_name("gpt-5.4-high") is True

    def test_claude_model(self):
        assert validate_model_name("claude-4.6-opus") is True

    def test_short_model(self):
        assert validate_model_name("o3") is True

    def test_empty_string_invalid(self):
        assert validate_model_name("") is False

    def test_starts_with_digit_invalid(self):
        assert validate_model_name("4gpt") is False

    def test_spaces_invalid(self):
        assert validate_model_name("gpt 4") is False

    def test_special_chars_invalid(self):
        assert validate_model_name("model@v2") is False

    def test_underscore_valid(self):
        assert validate_model_name("my_model") is True

    def test_slash_invalid(self):
        assert validate_model_name("org/model") is False


class TestDetectCursorModel:
    def test_returns_none_when_no_db(self):
        from pathlib import Path as _Path
        with patch("harness.commands.init.Path.home", return_value=_Path("/nonexistent")):
            assert _detect_cursor_model() is None

    def test_returns_none_on_error(self):
        with patch("harness.commands.init.Path.home", side_effect=OSError("no home")):
            assert _detect_cursor_model() is None


class TestStepEvaluatorModel:
    def test_choice_1_returns_inherit(self):
        with patch("harness.commands.init._detect_cursor_model", return_value=None):
            with patch("harness.commands.init.typer.prompt", return_value="1"):
                assert _step_evaluator_model() == "inherit"

    def test_choice_known_model(self):
        first_model = KNOWN_MODELS[0][0]
        with patch("harness.commands.init._detect_cursor_model", return_value=None):
            with patch("harness.commands.init.typer.prompt", return_value="2"):
                assert _step_evaluator_model() == first_model

    def test_custom_input_valid(self):
        custom_idx = str(2 + len(KNOWN_MODELS))
        with patch("harness.commands.init._detect_cursor_model", return_value=None):
            with patch(
                "harness.commands.init.typer.prompt",
                side_effect=[custom_idx, "my-custom-model"],
            ):
                assert _step_evaluator_model() == "my-custom-model"

    def test_custom_input_invalid_then_valid(self):
        custom_idx = str(2 + len(KNOWN_MODELS))
        with patch("harness.commands.init._detect_cursor_model", return_value=None):
            with patch(
                "harness.commands.init.typer.prompt",
                side_effect=[custom_idx, "", "gpt-4.1"],
            ):
                assert _step_evaluator_model() == "gpt-4.1"

    def test_detected_model_appears_as_option(self):
        with patch("harness.commands.init._detect_cursor_model", return_value="my-detected-v2"):
            with patch("harness.commands.init.typer.prompt", return_value="2"):
                assert _step_evaluator_model() == "my-detected-v2"


class TestUpdateGitignore:
    def test_creates_new_gitignore_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        set_lang("en")
        _update_gitignore(tmp_path)
        gi = tmp_path / ".gitignore"
        assert gi.exists()
        text = gi.read_text(encoding="utf-8")
        assert ".agents/state.json" in text
        assert ".agents/.stop" in text
        assert "# harness — do not track runtime state" in text

    def test_appends_to_existing_gitignore(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        set_lang("en")
        (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        _update_gitignore(tmp_path)
        text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert "node_modules/" in text
        assert ".agents/state.json" in text

    def test_skips_when_marker_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        set_lang("en")
        original = "foo\n.agents/state.json\nbar\n"
        (tmp_path / ".gitignore").write_text(original, encoding="utf-8")
        _update_gitignore(tmp_path)
        assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == original


class TestRunInitNonInteractive:
    @patch("harness.native.skill_gen.generate_native_artifacts")
    def test_creates_agents_layout_and_config(self, mock_gen, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        run_init(
            name="alpha-project",
            ci_command="pytest -q",
            non_interactive=True,
        )
        agents = tmp_path / ".agents"
        assert agents.is_dir()
        assert (agents / "tasks").is_dir()
        assert (agents / "archive").is_dir()
        cfg = agents / "config.toml"
        assert cfg.exists()
        body = cfg.read_text(encoding="utf-8")
        assert 'name = "alpha-project"' in body
        assert 'command = "pytest -q"' in body
        assert 'evaluator_model = "inherit"' in body
        vision = agents / "vision.md"
        assert vision.exists()
        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs.get("lang") == "en"

    @patch("harness.native.skill_gen.generate_native_artifacts")
    def test_updates_gitignore(self, _mock_gen, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        set_lang("en")
        run_init(non_interactive=True)
        gi = tmp_path / ".gitignore"
        assert gi.exists()
        assert ".agents/state.json" in gi.read_text(encoding="utf-8")


class TestRunInitReinit:
    """With --force and existing config, init skips wizard and regenerates artifacts."""

    @patch("harness.native.skill_gen.generate_native_artifacts", return_value=42)
    def test_reinit_skips_wizard_regenerates(self, mock_gen, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text(
            '[project]\nname = "existing"\nlang = "zh"\n'
            '[ci]\ncommand = "make test"\n'
            '[workflow]\ntrunk_branch = "main"\n',
            encoding="utf-8",
        )
        run_init(force=True)
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs.get("force") is True

    @patch("harness.native.skill_gen.generate_native_artifacts", return_value=10)
    def test_reinit_uses_config_lang(self, mock_gen, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text(
            '[project]\nname = "zh-proj"\nlang = "zh"\n'
            '[ci]\ncommand = "make test"\n'
            '[workflow]\ntrunk_branch = "main"\n',
            encoding="utf-8",
        )
        run_init(force=True)
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs.get("lang") == "zh"

    def test_reinit_bad_config_exits_with_error(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text("this is not valid toml [[[", encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            run_init(force=True)
        assert exc_info.value.exit_code == 1

    def test_no_force_config_exists_prompts_overwrite(self, monkeypatch, tmp_path):
        """Without --force, existing config triggers confirm prompt; declining exits."""
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text(
            '[project]\nname = "x"\n[ci]\ncommand = "t"\n',
            encoding="utf-8",
        )
        with patch("harness.commands.init.typer.confirm", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
                run_init()
            assert exc_info.value.exit_code == 0

    def test_force_no_config_runs_wizard(self, monkeypatch, tmp_path):
        """--force without existing config falls through to normal wizard."""
        monkeypatch.chdir(tmp_path)
        set_lang("en")
        with patch("harness.native.skill_gen.generate_native_artifacts"):
            run_init(non_interactive=True, force=True)
        assert (tmp_path / ".agents" / "config.toml").exists()

    @patch("harness.native.skill_gen.generate_native_artifacts")
    def test_no_force_config_exists_confirm_yes_overwrites(self, _mock_gen, monkeypatch, tmp_path):
        """Confirming overwrite re-runs the wizard and rewrites config."""
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text(
            '[project]\nname = "stale-proj"\n[ci]\ncommand = "t"\n',
            encoding="utf-8",
        )
        with patch("harness.commands.init.typer.confirm", return_value=True):
            set_lang("en")
            run_init(non_interactive=True)
        body = (agents / "config.toml").read_text(encoding="utf-8")
        assert 'name = "stale-proj"' not in body

    @patch("harness.native.skill_gen.generate_native_artifacts")
    def test_non_interactive_config_exists_skips_confirm(self, _mock_gen, monkeypatch, tmp_path):
        """non_interactive + existing config skips confirm prompt and overwrites."""
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / ".agents"
        agents.mkdir(parents=True)
        (agents / "config.toml").write_text(
            '[project]\nname = "stale"\n[ci]\ncommand = "x"\n',
            encoding="utf-8",
        )
        set_lang("en")
        run_init(non_interactive=True)
        body = (agents / "config.toml").read_text(encoding="utf-8")
        assert "stale" not in body
