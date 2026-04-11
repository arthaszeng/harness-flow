"""Tests for version_info core + CLI."""

from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from harness import __version__
from harness.cli import app
from harness.core.version_info import format_version_verbose, get_version_info

runner = CliRunner()


class TestGetVersionInfo:
    def test_returns_all_keys(self) -> None:
        info = get_version_info()
        expected_keys = {
            "harness_version",
            "python_version",
            "python_impl",
            "platform",
            "machine",
            "executable",
            "install_path",
        }
        assert set(info.keys()) == expected_keys

    def test_harness_version_matches(self) -> None:
        info = get_version_info()
        assert info["harness_version"] == __version__

    def test_python_version_matches(self) -> None:
        import platform

        info = get_version_info()
        assert info["python_version"] == platform.python_version()

    def test_executable_matches(self) -> None:
        info = get_version_info()
        assert info["executable"] == sys.executable


class TestFormatVersionVerbose:
    def test_contains_version(self) -> None:
        output = format_version_verbose()
        assert __version__ in output

    def test_contains_python(self) -> None:
        output = format_version_verbose()
        assert "Python" in output

    def test_custom_info(self) -> None:
        info = {
            "harness_version": "0.0.0",
            "python_version": "3.99.0",
            "python_impl": "TestPython",
            "platform": "TestOS",
            "machine": "test_arch",
            "executable": "/usr/bin/test_python",
            "install_path": "/test/path",
        }
        output = format_version_verbose(info)
        assert "0.0.0" in output
        assert "3.99.0" in output
        assert "TestPython" in output


class TestVersionCLI:
    def test_short_version_flag(self) -> None:
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert f"harness-flow {__version__}" in result.output

    def test_version_subcommand_default(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "Python" in result.output

    def test_version_subcommand_json(self) -> None:
        result = runner.invoke(app, ["version", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["harness_version"] == __version__
        assert "python_version" in data

    def test_version_subcommand_verbose(self) -> None:
        result = runner.invoke(app, ["version", "--verbose"])
        assert result.exit_code == 0
        assert "Platform" in result.output
        assert "Install path" in result.output
