"""赛博朋克风格终端 UI — 统一输出层

所有 Harness 终端输出通过 HarnessUI 类统一管理。
默认模式下 agent 子进程输出以滚动尾部展示（最新 5 行），
完成后自动收起为一行摘要。--verbose 恢复完整流式输出。
"""

from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Generator

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    pass

# ── 赛博配色 ──────────────────────────────────────────────────────

CYBER_THEME = Theme({
    "cyber.cyan": "bold #00ffff",
    "cyber.magenta": "bold #ff00ff",
    "cyber.green": "bold #39ff14",
    "cyber.yellow": "bold #ffff00",
    "cyber.red": "bold #ff0040",
    "cyber.dim": "dim #888888",
    "cyber.label": "#ff00ff",
    "cyber.ok": "#39ff14",
    "cyber.fail": "#ff0040",
    "cyber.warn": "#ffff00",
    "cyber.border": "#00ffff",
    "cyber.header": "bold #00ffff",
})

# ── ASCII Banner ──────────────────────────────────────────────────

_BANNER = r"""
 [cyber.cyan]██╗  ██╗ █████╗ ██████╗ ███╗   ██╗███████╗███████╗███████╗[/]
 [cyber.cyan]██║  ██║██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔════╝██╔════╝[/]
 [cyber.magenta]███████║███████║██████╔╝██╔██╗ ██║█████╗  ███████╗███████╗[/]
 [cyber.magenta]██╔══██║██╔══██║██╔══██╗██║╚██╗██║██╔══╝  ╚════██║╚════██║[/]
 [cyber.cyan]██║  ██║██║  ██║██║  ██║██║ ╚████║███████╗███████║███████║[/]
 [cyber.dim]╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚══════╝[/]"""

_TAIL_LINES = 5


# ── 滚动尾部 Renderable ──────────────────────────────────────────

class _TailRenderable:
    """Rich Live 中使用的滚动尾部渲染对象"""

    def __init__(self, label: str, driver_name: str, start: float) -> None:
        self.label = label
        self.driver_name = driver_name
        self.start = start
        self.lines: deque[str] = deque(maxlen=_TAIL_LINES)
        self.line_count = 0

    def add_line(self, line: str) -> None:
        self.lines.append(line.rstrip())
        self.line_count += 1

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        elapsed = time.monotonic() - self.start
        for line in self.lines:
            truncated = line[:options.max_width - 6] if len(line) > options.max_width - 6 else line
            yield Text(f"    ┊ {truncated}", style="cyber.dim")
        yield Text(
            f"    ┊ [{self.line_count} lines / {elapsed:.0f}s]",
            style="cyber.dim",
        )


# ── 主 UI 类 ─────────────────────────────────────────────────────

class HarnessUI:
    """Harness 赛博朋克终端 UI"""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.console = Console(stderr=True, theme=CYBER_THEME, highlight=False)

    # ── Banner & Session ──

    def banner(self, mode: str, version: str) -> None:
        self.console.print(_BANNER)
        self.console.print(
            f"                    [cyber.dim]v{version} // {mode} mode[/]",
        )
        self.console.print()

    def system_status(self, ides: dict[str, bool]) -> None:
        cursor_st = "[cyber.ok]ON[/]" if ides.get("cursor") else "[cyber.fail]OFF[/]"
        codex_st = "[cyber.ok]ON[/]" if ides.get("codex") else "[cyber.fail]OFF[/]"
        content = f"  IDE :: Cursor [{cursor_st}]  Codex [{codex_st}]"
        self.console.print(Panel(
            content,
            title="[cyber.header]SYSTEM[/]",
            border_style="cyber.border",
            padding=(0, 1),
        ))
        self.console.print()

    def session_end(self, completed: int, blocked: int, avg_score: float) -> None:
        content = (
            f"  completed [cyber.green]{completed}[/]"
            f"  │  blocked [cyber.red]{blocked}[/]"
            f"  │  avg [cyber.cyan]{avg_score:.1f}[/]"
        )
        self.console.print(Panel(
            content,
            title="[cyber.header]SESSION END[/]",
            border_style="cyber.border",
            padding=(0, 1),
        ))

    # ── Task ──

    def task_panel(self, task_id: str, requirement: str, branch: str) -> None:
        content = (
            f"  [cyber.label]TASK[/]    {task_id}\n"
            f"  [cyber.label]OBJ[/]     {requirement}\n"
            f"  [cyber.label]BRANCH[/]  [cyber.dim]{branch}[/]"
        )
        self.console.print()
        self.console.print(Panel(
            content,
            border_style="cyber.border",
            padding=(0, 1),
        ))

    def iteration_header(self, n: int, max_n: int) -> None:
        self.console.print()
        self.console.print(
            Rule(
                f"[cyber.magenta]◆ Iteration {n}/{max_n}[/]",
                style="cyber.dim",
            ),
        )

    def task_complete(self, task_id: str, score: float, elapsed: float) -> None:
        self.console.print()
        self.console.print(Rule(style="cyber.green"))
        self.console.print(
            f"  [cyber.green]✓ TASK COMPLETE[/]  "
            f"{task_id} // [cyber.cyan]{score:.1f}[/] // [cyber.dim]{elapsed:.0f}s[/]",
        )
        self.console.print(Rule(style="cyber.green"))

    def task_blocked(self, task_id: str, max_iter: int, *, reason: str = "") -> None:
        self.console.print()
        self.console.print(Rule(style="cyber.red"))
        detail = reason or f"max iterations {max_iter}"
        self.console.print(
            f"  [cyber.red]✗ TASK BLOCKED[/]  "
            f"{task_id} // [cyber.dim]{detail}[/]",
        )
        self.console.print(Rule(style="cyber.red"))

    # ── Agent Steps ──

    @contextmanager
    def agent_step(
        self, label: str, driver_name: str,
    ) -> Generator[Callable[[str], None] | None, None, None]:
        """agent 执行的上下文管理器。

        默认模式：Rich Live 展示滚动尾部，完成后自动擦除。
        verbose 模式：yield None，driver 原样输出到 stderr。
        """
        self.console.print(
            f"  [cyber.magenta]▸[/] [cyber.label]{label}[/] "
            f"[cyber.dim]// {driver_name}[/]",
        )

        if self.verbose:
            yield None
            return

        start = time.monotonic()
        tail = _TailRenderable(label, driver_name, start)

        def on_output(line: str) -> None:
            tail.add_line(line)

        try:
            with Live(
                tail,
                console=self.console,
                refresh_per_second=4,
                transient=True,
            ):
                yield on_output
        except Exception:
            yield on_output

    def step_done(
        self, label: str, elapsed: float, success: bool, detail: str = "",
        *, fail_tail: list[str] | None = None,
    ) -> None:
        if success:
            self.console.print(
                f"  [cyber.ok]✓[/] [cyber.label]{label}[/] "
                f"[cyber.dim]({elapsed:.0f}s)[/]"
                f"{'  ' + detail if detail else ''}",
            )
        else:
            self.console.print(
                f"  [cyber.fail]✗[/] [cyber.label]{label}[/] "
                f"[cyber.dim]({elapsed:.0f}s)[/]"
                f"{'  ' + detail if detail else ''}",
            )
            if fail_tail:
                for line in fail_tail[-3:]:
                    self.console.print(f"    [cyber.dim]┊ {line.rstrip()}[/]")

    # ── Strategist / Reflector 结果 ──

    def strategist_result(self, requirement: str, elapsed: float) -> None:
        self.console.print(
            f"  [cyber.ok]✓[/] [cyber.label][strategist][/] "
            f"[cyber.dim]target acquired ({elapsed:.0f}s)[/]",
        )
        self.console.print(f"    [cyber.cyan]→[/] {requirement}")

    def strategist_done(self, elapsed: float) -> None:
        self.console.print(
            f"  [cyber.ok]✓[/] [cyber.label][strategist][/] "
            f"[cyber.green]all objectives achieved[/] "
            f"[cyber.dim]({elapsed:.0f}s)[/]",
        )

    # ── 通用消息 ──

    def info(self, msg: str) -> None:
        self.console.print(f"  [cyber.dim]{msg}[/]")

    def warn(self, msg: str) -> None:
        self.console.print(f"  [cyber.warn]![/] {msg}")

    def error(self, msg: str) -> None:
        self.console.print(f"  [cyber.fail]✗[/] {msg}", style="")

    def safety_stop(self, reason: str) -> None:
        self.console.print(f"\n  [cyber.yellow]▪ [safety][/] {reason}")


# ── 单例管理 ─────────────────────────────────────────────────────

_ui: HarnessUI | None = None


def init_ui(verbose: bool = False) -> HarnessUI:
    """初始化全局 UI 单例（由 CLI 入口调用）"""
    global _ui
    _ui = HarnessUI(verbose=verbose)
    return _ui


def get_ui() -> HarnessUI:
    """获取全局 UI（未初始化时创建默认实例）"""
    global _ui
    if _ui is None:
        _ui = HarnessUI()
    return _ui
