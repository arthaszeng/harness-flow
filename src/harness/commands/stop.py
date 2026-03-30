"""harness stop — graceful stop"""

from __future__ import annotations

from pathlib import Path

import typer

from harness.i18n import t
from harness.orchestrator.safety import write_stop_signal


def run_stop() -> None:
    """Write stop signal; current task stops after finishing its current phase."""
    agents_dir = Path.cwd() / ".agents"
    write_stop_signal(agents_dir)
    typer.echo(t("stop.sent"))
    typer.echo(t("stop.file"))
