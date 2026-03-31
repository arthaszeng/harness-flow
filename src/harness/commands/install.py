"""harness install — install agent definitions to local IDE"""

from __future__ import annotations

import importlib.resources
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from harness.core.config import HarnessConfig
from harness.i18n import get_lang, t

# agent file → target path mapping
_CURSOR_AGENTS = {
    "builder.md": "harness-builder.md",
    "reflector.md": "harness-reflector.md",
}
_CODEX_AGENTS = {
    "planner.toml": "harness-planner.toml",
    "evaluator.toml": "harness-evaluator.toml",
    "strategist.toml": "harness-strategist.toml",
    "reflector.toml": "harness-reflector.toml",
    "advisor.toml": "harness-advisor.toml",
    "alignment_evaluator.toml": "harness-alignment-evaluator.toml",
}


def _agents_pkg_dir() -> Path:
    """Return the packaged agents/ directory path."""
    pkg = importlib.resources.files("harness")
    return Path(str(pkg)).parent.parent / "agents"


def _resolve_install_lang(lang: str | None) -> str:
    """Pick install language: explicit arg, then config, then UI lang, else en."""
    if lang is not None:
        return lang if lang in ("en", "zh") else "en"
    try:
        cfg = HarnessConfig.load()
        pl = cfg.project.lang
        if pl in ("en", "zh"):
            return pl
    except Exception:
        pass
    gl = get_lang()
    return gl if gl in ("en", "zh") else "en"


def _detect_ide() -> dict[str, bool]:
    """Detect locally installed IDE CLIs."""
    return {
        "cursor": shutil.which("cursor") is not None,
        "codex": shutil.which("codex") is not None,
    }


def _install_cursor_agents(source_dir: Path, *, force: bool, lang: str) -> int:
    """Install Cursor agent definitions."""
    target_dir = Path.home() / ".cursor" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    src_dir = source_dir / "cursor"
    if lang == "zh":
        zh_dir = src_dir / "zh"
        if zh_dir.is_dir():
            src_dir = zh_dir
    for src_name, dst_name in _CURSOR_AGENTS.items():
        src = src_dir / src_name
        dst = target_dir / dst_name
        if not src.exists():
            typer.echo(t("install.warn_missing", src=src), err=True)
            continue
        if dst.exists() and not force:
            typer.echo(t("install.skip_exists", dst=dst))
            continue
        shutil.copy2(src, dst)
        typer.echo(f"  [ok] {dst}")
        installed += 1
    return installed


def _install_codex_agents(source_dir: Path, *, force: bool, lang: str) -> int:
    """Install Codex agent definitions."""
    target_dir = Path.home() / ".codex" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    src_dir = source_dir / "codex"
    if lang == "zh":
        zh_dir = src_dir / "zh"
        if zh_dir.is_dir():
            src_dir = zh_dir
    for src_name, dst_name in _CODEX_AGENTS.items():
        src = src_dir / src_name
        dst = target_dir / dst_name
        if not src.exists():
            typer.echo(t("install.warn_missing", src=src), err=True)
            continue
        if dst.exists() and not force:
            typer.echo(t("install.skip_exists", dst=dst))
            continue
        shutil.copy2(src, dst)
        typer.echo(f"  [ok] {dst}")
        installed += 1
    return installed


def _run_cli_install(cmd: list[str], label: str) -> bool:
    """Run an external CLI install command with live output. Returns True on success."""
    typer.echo(t("install.cli_running", label=label))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=sys.stderr,
            stderr=sys.stderr,
        )
        proc.wait(timeout=120)
        if proc.returncode == 0:
            typer.echo(t("install.cli_ok", label=label))
            return True
        typer.echo(t("install.cli_fail", label=label), err=True)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        typer.echo(t("install.cli_timeout", label=label), err=True)
    except Exception as exc:
        typer.echo(t("install.cli_error", label=label, error=str(exc)), err=True)
    return False


def _try_install_cursor_agent() -> bool:
    """Offer to install cursor-agent via official installer script."""
    if not shutil.which("curl"):
        typer.echo(t("install.curl_missing"))
        return False
    if not typer.confirm(t("install.cursor_agent_confirm"), default=True):
        return False
    return _run_cli_install(
        ["bash", "-c", "curl https://cursor.com/install -fsS | bash"],
        "Cursor Agent",
    )


def _try_install_codex_cli() -> bool:
    """Offer to install Codex CLI via npm."""
    npm = shutil.which("npm")
    if not npm:
        typer.echo(t("install.npm_missing"))
        return False
    if not typer.confirm(t("install.codex_cli_confirm"), default=True):
        return False
    return _run_cli_install(["npm", "install", "-g", "@openai/codex"], "Codex CLI")


def _probe_ides(ides: dict[str, bool]) -> dict[str, bool]:
    """Run functional probes, offer guided install for missing/broken CLIs.

    Returns a dict with functional readiness (may upgrade False → True after install).
    """
    from harness.drivers.codex import CodexDriver
    from harness.drivers.cursor import CursorDriver

    ready = dict(ides)

    # ── Cursor ────────────────────────────────────────────────────
    if ides["cursor"]:
        probe = CursorDriver().probe()
        if probe.available:
            typer.echo(t("install.cursor_ok"))
        else:
            typer.echo(t("install.cursor_not_ready"))
            if _try_install_cursor_agent():
                reprobe = CursorDriver().probe()
                if reprobe.available:
                    typer.echo(t("install.cursor_ok"))
                else:
                    ready["cursor"] = False
            else:
                ready["cursor"] = False
    else:
        typer.echo(t("install.cursor_missing"))

    # ── Codex ─────────────────────────────────────────────────────
    if ides["codex"]:
        probe = CodexDriver().probe()
        if probe.available:
            typer.echo(t("install.codex_ok"))
        else:
            typer.echo(t("install.codex_not_ready"))
            if _try_install_codex_cli():
                reprobe = CodexDriver().probe()
                if reprobe.available:
                    typer.echo(t("install.codex_ok"))
                else:
                    ready["codex"] = False
            else:
                ready["codex"] = False
    else:
        typer.echo(t("install.codex_missing"))
        if _try_install_codex_cli():
            ides["codex"] = True
            ready["codex"] = True
            typer.echo(t("install.codex_ok"))

    return ready


def run_install(*, force: bool = False, lang: str | None = None) -> None:
    """Run install: preflight, then copy agent files."""
    resolved = _resolve_install_lang(lang)
    typer.echo(t("install.title"))

    ides = _detect_ide()
    typer.echo(t("install.env_check"))
    _probe_ides(ides)

    if not any(ides.values()):
        typer.echo(t("install.no_ide"), err=True)
        raise typer.Exit(1)

    source_dir = _agents_pkg_dir()
    if not source_dir.exists():
        typer.echo(t("install.no_source", path=source_dir), err=True)
        raise typer.Exit(1)

    total = 0
    typer.echo()

    if ides["cursor"]:
        typer.echo(t("install.cursor_agents"))
        total += _install_cursor_agents(source_dir, force=force, lang=resolved)

    if ides["codex"]:
        typer.echo(t("install.codex_agents"))
        total += _install_codex_agents(source_dir, force=force, lang=resolved)

    typer.echo(t("install.done", count=total))
