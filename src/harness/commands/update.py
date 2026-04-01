"""harness update — self-update, reinstall artifacts, and migrate config."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from harness import __version__
from harness.i18n import t


def _get_latest_version() -> str | None:
    """Query PyPI for the latest harness-orchestrator version."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "harness-orchestrator"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            # Output: "harness-orchestrator (X.Y.Z)"
            for line in result.stdout.splitlines():
                if "harness-orchestrator" in line and "(" in line:
                    return line.split("(")[1].split(")")[0].strip()
    except Exception:
        pass
    return None


def _pip_upgrade() -> bool:
    """Run pip install --upgrade harness-orchestrator."""
    typer.echo(t("update.upgrading"))
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "harness-orchestrator"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        typer.echo(t("update.upgrade_ok"))
        return True
    typer.echo(t("update.upgrade_fail"))
    if result.stderr:
        for line in result.stderr.strip().splitlines()[-3:]:
            typer.echo(f"    {line}")
    return False


def _migrate_config(project_root: Path) -> int:
    """Check .agents/config.toml for missing/deprecated keys. Returns count of warnings."""
    config_path = project_root / ".agents" / "config.toml"
    if not config_path.exists():
        return 0

    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        typer.echo(t("update.config_parse_error", path=str(config_path)))
        return 1

    warnings = 0

    # Check for recommended sections
    recommended_sections = {
        "project": "project name and language",
        "ci": "CI gate command",
        "workflow": "workflow mode and iteration settings",
    }
    for section, desc in recommended_sections.items():
        if section not in data:
            typer.echo(t("update.config_missing_section", section=section, desc=desc))
            warnings += 1

    # Check for new keys that may have been added in recent versions
    workflow = data.get("workflow", {})
    new_workflow_keys = {
        "mode": "orchestrator",
        "trunk_branch": "main",
    }
    for key, default in new_workflow_keys.items():
        if key not in workflow and "workflow" in data:
            typer.echo(t("update.config_new_key", section="workflow", config_key=key, default=default))
            warnings += 1

    # Check for deprecated keys (none yet, but extensible)
    deprecated: list[tuple[str, str, str]] = [
        # ("old_section.old_key", "replacement", "version"),
    ]
    for old_key, replacement, since_version in deprecated:
        parts = old_key.split(".")
        section_data = data
        found = True
        for p in parts:
            if isinstance(section_data, dict) and p in section_data:
                section_data = section_data[p]
            else:
                found = False
                break
        if found:
            typer.echo(t("update.config_deprecated", config_key=old_key, replacement=replacement, version=since_version))
            warnings += 1

    if warnings == 0:
        typer.echo(t("update.config_ok"))

    return warnings


def run_update(*, check: bool = False) -> None:
    """Execute the harness update workflow."""
    typer.echo(t("update.title"))
    typer.echo(t("update.current_version", version=__version__))

    # Step 1: Check for new version
    typer.echo(t("update.checking"))
    latest = _get_latest_version()

    if latest is None:
        typer.echo(t("update.check_failed"))
        if check:
            raise typer.Exit(1)
    elif latest == __version__:
        typer.echo(t("update.up_to_date"))
    else:
        typer.echo(t("update.new_version", version=latest))
        if check:
            raise typer.Exit(0)

        # Step 2: Self-update via pip
        if not _pip_upgrade():
            typer.echo(t("update.skip_reinstall"))
            raise typer.Exit(1)

    if check:
        raise typer.Exit(0)

    # Step 3: Reinstall agent definitions (equivalent to harness install --force)
    typer.echo(t("update.reinstall"))
    from harness.commands.install import run_install
    run_install(force=True, lang=None)

    # Step 4: Config migration
    typer.echo(t("update.migrate_title"))
    project_root = Path.cwd()
    warning_count = _migrate_config(project_root)

    # Summary
    typer.echo(t("update.done", warnings=warning_count))
