"""harness install — 安装 agent 定义到本地 IDE"""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path

import typer

# agent 文件 → 目标路径的映射
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
}


def _agents_pkg_dir() -> Path:
    """获取打包在项目中的 agents/ 目录路径"""
    pkg = importlib.resources.files("harness")
    # src/harness/ → 向上两级到项目根 → agents/
    return Path(str(pkg)).parent.parent / "agents"


def _detect_ide() -> dict[str, bool]:
    """检测本地安装的 IDE CLI"""
    return {
        "cursor": shutil.which("cursor") is not None,
        "codex": shutil.which("codex") is not None,
    }


def _install_cursor_agents(source_dir: Path, *, force: bool) -> int:
    """安装 Cursor agent 定义"""
    target_dir = Path.home() / ".cursor" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    src_dir = source_dir / "cursor"
    for src_name, dst_name in _CURSOR_AGENTS.items():
        src = src_dir / src_name
        dst = target_dir / dst_name
        if not src.exists():
            typer.echo(f"  [warn] 源文件不存在: {src}", err=True)
            continue
        if dst.exists() and not force:
            typer.echo(f"  [skip] 已存在: {dst} (用 --force 覆盖)")
            continue
        shutil.copy2(src, dst)
        typer.echo(f"  [ok] {dst}")
        installed += 1
    return installed


def _install_codex_agents(source_dir: Path, *, force: bool) -> int:
    """安装 Codex agent 定义"""
    target_dir = Path.home() / ".codex" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    src_dir = source_dir / "codex"
    for src_name, dst_name in _CODEX_AGENTS.items():
        src = src_dir / src_name
        dst = target_dir / dst_name
        if not src.exists():
            typer.echo(f"  [warn] 源文件不存在: {src}", err=True)
            continue
        if dst.exists() and not force:
            typer.echo(f"  [skip] 已存在: {dst} (用 --force 覆盖)")
            continue
        shutil.copy2(src, dst)
        typer.echo(f"  [ok] {dst}")
        installed += 1
    return installed


def run_install(*, force: bool = False) -> None:
    """执行安装流程：预检 → 复制 agent 文件"""
    typer.echo("harness install — 安装 agent 定义\n")

    # 环境预检
    ides = _detect_ide()
    typer.echo("环境检测:")
    typer.echo(f"  Cursor CLI: {'✓' if ides['cursor'] else '✗ 未找到'}")
    typer.echo(f"  Codex CLI:  {'✓' if ides['codex'] else '✗ 未找到'}")

    if not any(ides.values()):
        typer.echo("\n[error] 未检测到 Cursor 或 Codex CLI，至少需要安装一个。", err=True)
        raise typer.Exit(1)

    source_dir = _agents_pkg_dir()
    if not source_dir.exists():
        typer.echo(f"\n[error] agent 源文件目录不存在: {source_dir}", err=True)
        raise typer.Exit(1)

    total = 0
    typer.echo()

    if ides["cursor"]:
        typer.echo("安装 Cursor agents:")
        total += _install_cursor_agents(source_dir, force=force)

    if ides["codex"]:
        typer.echo("安装 Codex agents:")
        total += _install_codex_agents(source_dir, force=force)

    typer.echo(f"\n完成: {total} 个 agent 定义已安装。")
