"""Tests for harness install — native artifact generation only."""

from __future__ import annotations

from unittest.mock import patch

from harness.commands.install import _resolve_install_lang, run_install


class TestResolveInstallLang:
    def test_explicit_en_zh(self):
        assert _resolve_install_lang("en") == "en"
        assert _resolve_install_lang("zh") == "zh"

    def test_explicit_other_defaults_en(self):
        assert _resolve_install_lang("fr") == "en"

    @patch("harness.commands.install.HarnessConfig.load")
    def test_from_config(self, mock_load):
        mock_cfg = mock_load.return_value
        mock_cfg.project.lang = "zh"
        assert _resolve_install_lang(None) == "zh"

    @patch("harness.commands.install.HarnessConfig.load", side_effect=OSError("no config"))
    @patch("harness.commands.install.get_lang", return_value="en")
    def test_fallback_ui_lang(self, _mock_lang, _mock_load):
        assert _resolve_install_lang(None) == "en"


class TestRunInstallNativeOnly:
    """run_install resolves language, prints title, generates native artifacts, prints done."""

    @patch("harness.commands.install._install_native_mode", return_value=42)
    def test_invokes_native_mode_with_resolved_lang(self, mock_native, capsys):
        run_install(force=True, lang="zh")
        mock_native.assert_called_once()
        kwargs = mock_native.call_args.kwargs
        assert kwargs["lang"] == "zh"
        assert kwargs["force"] is True
        out = capsys.readouterr().out
        assert "42" in out or "完成" in out or "Done" in out

    @patch("harness.commands.install._install_native_mode", return_value=0)
    def test_done_shows_zero_count(self, _mock_native, capsys):
        run_install(force=False, lang="en")
        out = capsys.readouterr().out
        assert "0" in out
