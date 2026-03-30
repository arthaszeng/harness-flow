"""harness vision — 交互式 vision 创建/更新"""

from __future__ import annotations

import time
from pathlib import Path

import typer

from harness.core.config import HarnessConfig
from harness.core.ui import get_ui
from harness.drivers.resolver import DriverResolver
from harness.orchestrator.vision_flow import (
    AdvisorOutput,
    gather_context,
    invoke_advisor,
    write_vision,
)


def run_vision() -> None:
    """交互式 vision 生成：用户输入 → Advisor 展开 → 确认 → 写入"""
    project_root = Path.cwd()
    agents_dir = project_root / ".agents"
    ui = get_ui()

    if not (agents_dir / "config.toml").exists():
        ui.error("未找到 .agents/config.toml，请先运行 `harness init`")
        raise typer.Exit(1)

    config = HarnessConfig.load(project_root)
    resolver = DriverResolver(config)

    avail = resolver.available_drivers
    if not any(avail.values()):
        ui.error("未检测到 Cursor 或 Codex CLI")
        raise typer.Exit(1)

    # Phase 1: 收集上下文
    ui.info("[vision] 收集项目上下文...")
    ctx = gather_context(project_root)
    _show_context_summary(ctx, agents_dir, ui)

    # Phase 2: 用户输入循环
    user_input = typer.prompt(
        "\n请用一句话描述你想让项目实现什么（或你想调整的方向）"
    )

    driver = resolver.resolve("advisor")
    agent_name = resolver.agent_name("advisor")

    while True:
        t0 = time.monotonic()
        with ui.agent_step("[vision] advisor 展开需求", driver.name) as on_out:
            result = invoke_advisor(
                driver, agent_name, ctx, user_input, project_root,
                on_output=on_out,
            )
        elapsed = time.monotonic() - t0

        if not result.vision_content:
            ui.step_done("[vision] advisor", elapsed, False, "未能生成有效 vision")
            user_input = typer.prompt("请换一种方式描述你的需求")
            continue

        ui.step_done("[vision] advisor", elapsed, True, "vision 已生成")

        # 显示追问
        if result.questions:
            ui.info("[vision] 有几个问题想确认：")
            for i, q in enumerate(result.questions, 1):
                ui.info(f"  {i}. {q}")
            answers = typer.prompt("\n请回答以上问题（或直接回车跳过）", default="")
            if answers.strip():
                user_input = f"{user_input}\n\n补充说明：{answers}"
                continue

        # 显示生成的 vision
        ui.console.print()
        ui.console.print(
            f"  [cyber.cyan]{'─' * 50}[/]"
        )
        ui.console.print("  [cyber.label]展开后的 Vision[/]")
        ui.console.print(
            f"  [cyber.cyan]{'─' * 50}[/]"
        )
        ui.console.print()
        for line in result.vision_content.split("\n"):
            ui.console.print(f"  {line}")
        ui.console.print()
        ui.console.print(
            f"  [cyber.cyan]{'─' * 50}[/]"
        )

        # Phase 3: 确认
        while True:
            choice = typer.prompt(
                "这个 vision 准确吗？ [y=确认写入 / e=补充修改 / r=重新生成]",
                default="y",
            ).strip().lower()
            if choice in ("y", "e", "r"):
                break
            ui.warn("请输入 y、e 或 r")

        if choice == "y":
            size = write_vision(agents_dir, result.vision_content)
            ui.info(f"[vision] 已写入 .agents/vision.md ({size} bytes)")
            break
        elif choice == "e":
            extra = typer.prompt("请补充你想调整的内容")
            user_input = f"{user_input}\n\n用户补充：{extra}"
        else:
            user_input = typer.prompt("请重新描述你的需求")


def _show_context_summary(ctx, agents_dir: Path, ui) -> None:
    """显示收集到的上下文摘要"""
    vision_path = agents_dir / "vision.md"
    if vision_path.exists():
        size = vision_path.stat().st_size
        ui.info(f"  vision.md: 存在 ({size} bytes)")
    else:
        ui.info("  vision.md: 不存在")

    reflection_path = agents_dir / "reflection.md"
    if reflection_path.exists():
        ui.info("  reflection.md: 存在")

    progress_path = agents_dir / "progress.md"
    if progress_path.exists():
        ui.info("  progress.md: 存在")

    doc_count = len(ctx.doc_summaries)
    if doc_count:
        ui.info(f"  doc/: {doc_count} 个文档")
