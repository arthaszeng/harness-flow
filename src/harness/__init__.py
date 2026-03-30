"""harness-orchestrator: GAN 三角架构多 Agent 自主开发框架"""

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("harness-orchestrator")
except Exception:
    __version__ = "0.0.0-dev"
