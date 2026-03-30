"""Harness CLI 主入口"""

import typer

from harness import __version__

app = typer.Typer(
    name="harness",
    help="GAN 三角架构多 Agent 自主开发框架",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"harness-orchestrator {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="显示版本号",
    ),
) -> None:
    """GAN 三角架构多 Agent 自主开发框架"""


@app.command()
def install(
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已有 agent 定义"),
) -> None:
    """安装 agent 定义到本地 IDE（Cursor / Codex）"""
    from harness.commands.install import run_install
    run_install(force=force)


@app.command()
def init(
    name: str = typer.Option("", "--name", "-n", help="项目名称"),
    ci_command: str = typer.Option("", "--ci", help="CI 命令（如 make test）"),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-y", help="跳过交互式向导，使用默认值",
    ),
) -> None:
    """在当前项目中初始化 harness 配置（交互式向导）"""
    from harness.commands.init import run_init
    run_init(name=name, ci_command=ci_command, non_interactive=non_interactive)


@app.command()
def vision() -> None:
    """交互式创建或更新项目愿景（.agents/vision.md）"""
    from harness.commands.vision_cmd import run_vision
    run_vision()


@app.command()
def run(
    requirement: str = typer.Argument(..., help="需求描述"),
    resume: bool = typer.Option(False, "--resume", "-r", help="从上次中断处恢复"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="显示完整 agent 输出"),
) -> None:
    """执行单个开发任务"""
    from harness.commands.run import run_task
    run_task(requirement=requirement, resume=resume, verbose=verbose)


@app.command()
def auto(
    resume: bool = typer.Option(False, "--resume", "-r", help="从上次中断处恢复"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="显示完整 agent 输出"),
) -> None:
    """启动自治开发循环"""
    from harness.commands.auto import run_auto
    run_auto(resume=resume, verbose=verbose)


@app.command()
def status() -> None:
    """查看当前进度和状态"""
    from harness.commands.status import run_status
    run_status()


@app.command()
def stop() -> None:
    """优雅停止当前运行的任务"""
    from harness.commands.stop import run_stop
    run_stop()
