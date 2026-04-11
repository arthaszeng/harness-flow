"""Runtime version and environment information for diagnostics."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from harness import __version__


def get_version_info() -> dict:
    """Collect harness version plus Python/platform/install-path metadata."""
    harness_pkg = Path(__file__).resolve().parent.parent
    return {
        "harness_version": __version__,
        "python_version": platform.python_version(),
        "python_impl": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": sys.executable,
        "install_path": str(harness_pkg),
    }


def format_version_verbose(info: dict | None = None) -> str:
    """Human-readable multi-line version output."""
    if info is None:
        info = get_version_info()
    lines = [
        f"harness-flow {info['harness_version']}",
        f"Python       {info['python_version']} ({info['python_impl']})",
        f"Platform     {info['platform']}",
        f"Machine      {info['machine']}",
        f"Executable   {info['executable']}",
        f"Install path {info['install_path']}",
    ]
    return "\n".join(lines)
