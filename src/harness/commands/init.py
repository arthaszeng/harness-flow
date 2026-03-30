"""harness init — 智能项目初始化向导"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import jinja2
import typer

from harness.core.scanner import ProjectScan, format_scan_report, scan_project


def _load_template(name: str) -> jinja2.Template:
    import importlib.resources
    pkg = importlib.resources.files("harness") / "templates"
    tmpl_path = Path(str(pkg)) / name
    return jinja2.Template(tmpl_path.read_text(encoding="utf-8"))


def _prompt_choice(prompt_text: str, n_options: int, default: int = 1) -> int:
    """通用编号选择，返回 1-based 选项号"""
    while True:
        raw = typer.prompt(prompt_text, default=str(default)).strip()
        try:
            choice = int(raw)
            if 1 <= choice <= n_options:
                return choice
        except ValueError:
            pass
        typer.echo(f"  请输入 1-{n_options} 之间的数字")


# ── Step 1: 项目信息 ──────────────────────────────────────────────

def _step_project_info(
    project_root: Path, *, name_override: str = "",
) -> tuple[str, str]:
    typer.echo("\nStep 1/6  项目信息")
    name = name_override or typer.prompt(
        "  项目名称", default=project_root.name,
    )
    description = typer.prompt("  项目描述（可选）", default="")
    return name, description


# ── Step 2: IDE 环境 ──────────────────────────────────────────────

def _step_ide_setup() -> dict[str, bool]:
    typer.echo("\nStep 2/6  IDE 环境")
    ides = {
        "cursor": shutil.which("cursor") is not None,
        "codex": shutil.which("codex") is not None,
    }
    typer.echo(f"  Cursor CLI: {'ok' if ides['cursor'] else '未检测到'}")
    typer.echo(f"  Codex CLI:  {'ok' if ides['codex'] else '未检测到'}")

    if not any(ides.values()):
        typer.echo("\n  [error] 至少需要安装 Cursor 或 Codex CLI。", err=True)
        raise typer.Exit(1)

    do_install = typer.confirm("  安装 agent 定义到本地 IDE?", default=True)
    if do_install:
        from harness.commands.install import run_install
        run_install(force=True)

    return ides


# ── Step 3: 驱动模式 ──────────────────────────────────────────────

def _step_driver_mode(ides: dict[str, bool]) -> tuple[str, dict[str, str]]:
    """返回 (mode, roles_dict)"""
    typer.echo("\nStep 3/6  驱动模式")

    both = ides["cursor"] and ides["codex"]
    cursor_only = ides["cursor"] and not ides["codex"]
    codex_only = ides["codex"] and not ides["cursor"]

    if both:
        typer.echo("  检测到 Cursor + Codex，可选：")
        typer.echo("  1. auto -- Builder->Cursor, 其余->Codex（推荐）")
        typer.echo("  2. cursor -- 全部使用 Cursor")
        typer.echo("  3. codex  -- 全部使用 Codex")
        choice = _prompt_choice("  选择", 3, default=1)
        mode = ["auto", "cursor", "codex"][choice - 1]
    elif cursor_only:
        typer.echo("  仅检测到 Cursor，将使用 cursor 模式")
        mode = "cursor"
    else:
        typer.echo("  仅检测到 Codex，将使用 codex 模式")
        mode = "codex"

    # auto 模式下的推荐角色分配
    roles: dict[str, str] = {}
    if mode == "auto" and both:
        roles = {
            "planner": "codex",
            "builder": "cursor",
            "evaluator": "codex",
        }

    return mode, roles


# ── Step 4: CI 门禁 ──────────────────────────────────────────────

def _step_ci_command(
    project_root: Path,
    ides: dict[str, bool],
    *,
    ci_override: str = "",
) -> str:
    if ci_override:
        return ci_override

    typer.echo("\nStep 4/6  CI 门禁")
    typer.echo("  分析项目结构...")

    scan = scan_project(project_root)
    report = format_scan_report(scan)

    if report:
        for line in report:
            typer.echo(f"    发现 {line}")
    else:
        typer.echo("    未发现常见 CI 配置文件")

    suggestions = scan.suggested_commands
    if suggestions:
        typer.echo("\n  推荐的 CI 命令:")
        for i, (cmd, desc) in enumerate(suggestions, 1):
            label = "（推荐）" if i == 1 else ""
            typer.echo(f"  {i}. {cmd} -- {desc}{label}")

        ai_idx = len(suggestions) + 1
        custom_idx = ai_idx + 1
        typer.echo(f"  {ai_idx}. 让 AI 深度分析项目后推荐")
        typer.echo(f"  {custom_idx}. 自定义输入")

        choice = _prompt_choice("  选择", custom_idx, default=1)

        if choice <= len(suggestions):
            selected = suggestions[choice - 1][0]
            typer.echo(f"  -> {selected}")
            return selected
        elif choice == ai_idx:
            return _ai_suggest_ci(project_root, ides, scan)
        else:
            return typer.prompt("  请输入 CI 命令")
    else:
        typer.echo("\n  未找到自动建议，请选择：")
        typer.echo("  1. 让 AI 深度分析项目后推荐")
        typer.echo("  2. 自定义输入")
        typer.echo("  3. 跳过（不配置 CI 门禁）")
        choice = _prompt_choice("  选择", 3, default=1)

        if choice == 1:
            return _ai_suggest_ci(project_root, ides, scan)
        elif choice == 2:
            return typer.prompt("  请输入 CI 命令")
        else:
            return ""


def _ai_suggest_ci(
    project_root: Path, ides: dict[str, bool], scan: ProjectScan,
) -> str:
    """用 AI agent 分析项目并推荐 CI 命令"""
    from harness.core.config import HarnessConfig
    from harness.drivers.codex import CodexDriver
    from harness.drivers.cursor import CursorDriver

    # 选择可用的 driver
    driver = None
    if ides.get("codex"):
        driver = CodexDriver()
    elif ides.get("cursor"):
        driver = CursorDriver()

    if not driver:
        typer.echo("  [warn] 无可用 IDE，跳过 AI 分析")
        return typer.prompt("  请输入 CI 命令", default="make test")

    # 构建轻量 prompt
    report_lines = format_scan_report(scan)
    report_text = "\n".join(f"- {l}" for l in report_lines) if report_lines else "无"

    prompt = f"""\
分析以下项目，推荐一个适合作为自动化 CI 门禁的命令。
要求：命令应覆盖代码质量检查和单元测试，但不应包含慢速的冒烟测试或需要网络的操作。

项目根目录: {project_root}
项目结构发现:
{report_text}

请直接输出推荐的命令（一行），不要其他解释。例如：make check test
"""

    typer.echo("  [AI] 分析中...")
    t0 = time.monotonic()
    result = driver.invoke("harness-advisor", prompt, project_root, readonly=True, timeout=120)
    elapsed = time.monotonic() - t0
    typer.echo(f"  [AI] 完成 ({elapsed:.0f}s)")

    if result.success and result.output.strip():
        # 提取第一行非空内容作为命令
        for line in result.output.strip().split("\n"):
            line = line.strip().strip("`").strip()
            if line and not line.startswith("#") and not line.startswith("推荐"):
                typer.echo(f"  AI 推荐: {line}")
                use_it = typer.confirm("  使用这个命令?", default=True)
                if use_it:
                    return line
                break

    return typer.prompt("  请输入 CI 命令", default="make test")


# ── Step 5: Memverse ──────────────────────────────────────────────

def _step_memverse(
    project_root: Path,
    driver_mode: str,
) -> tuple[bool, str, str]:
    """返回 (enabled, driver, domain_prefix)"""
    typer.echo("\nStep 5/6  Memverse 记忆集成")
    typer.echo("  Memverse 可在 agent 反思时将关键决策持久化到长期记忆系统。")
    typer.echo("  1. 开启（推荐）")
    typer.echo("  2. 关闭")
    choice = _prompt_choice("  选择", 2, default=1)

    if choice == 2:
        return False, "auto", ""

    # driver 模式：跟随全局 driver 或独立指定
    mv_driver = driver_mode
    typer.echo(f"\n  Memverse driver 将跟随全局设置: {driver_mode}")
    typer.echo(f"  所有可用 IDE 均可写入 Memverse。")

    domain = typer.prompt("  Domain prefix（用于区分项目）", default=project_root.name)

    return True, mv_driver, domain


# ── Step 6: Vision ────────────────────────────────────────────────

def _step_vision(agents_dir: Path) -> bool:
    """返回 True 表示用户选择立即创建 vision"""
    typer.echo("\nStep 6/6  Vision")
    typer.echo("  1. 现在用 harness vision 交互式生成（推荐）")
    typer.echo("  2. 跳过，稍后手动编辑 .agents/vision.md")
    choice = _prompt_choice("  选择", 2, default=1)
    return choice == 1


# ── 主流程 ────────────────────────────────────────────────────────

def run_init(
    *,
    name: str = "",
    ci_command: str = "",
    non_interactive: bool = False,
) -> None:
    """智能初始化向导"""
    project_root = Path.cwd()
    agents_dir = project_root / ".agents"

    # 已存在检查
    if (agents_dir / "config.toml").exists():
        overwrite = typer.confirm(
            ".agents/config.toml 已存在，是否覆盖?", default=False,
        )
        if not overwrite:
            typer.echo("已取消。")
            raise typer.Exit(0)

    typer.echo("\n  HARNESS -- 项目初始化向导")

    if non_interactive:
        proj_name = name or project_root.name
        description = ""
        ides = {
            "cursor": shutil.which("cursor") is not None,
            "codex": shutil.which("codex") is not None,
        }
        driver_mode = "auto"
        roles: dict[str, str] = {}
        ci = ci_command or "make test"
        memverse_enabled, memverse_driver, memverse_domain = False, "auto", ""
        launch_vision = False
    else:
        # Step 1
        proj_name, description = _step_project_info(project_root, name_override=name)
        # Step 2
        ides = _step_ide_setup()
        # Step 3
        driver_mode, roles = _step_driver_mode(ides)
        # Step 4
        ci = _step_ci_command(project_root, ides, ci_override=ci_command)
        # Step 5
        memverse_enabled, memverse_driver, memverse_domain = _step_memverse(
            project_root, driver_mode,
        )
        # Step 6
        launch_vision = _step_vision(agents_dir)

    # 创建目录结构
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "tasks").mkdir(exist_ok=True)
    (agents_dir / "archive").mkdir(exist_ok=True)

    # 生成 config.toml
    tmpl = _load_template("config.toml.j2")
    config_content = tmpl.render(
        project_name=proj_name,
        description=description,
        ci_command=ci,
        driver_mode=driver_mode,
        roles=roles,
        memverse_enabled="true" if memverse_enabled else "false",
        memverse_driver=memverse_driver,
        memverse_domain=memverse_domain,
    )
    (agents_dir / "config.toml").write_text(config_content, encoding="utf-8")

    # 生成 vision.md（仅首次或向导模式）
    vision_path = agents_dir / "vision.md"
    if not vision_path.exists() and not launch_vision:
        tmpl = _load_template("vision.md.j2")
        vision_content = tmpl.render(project_name=proj_name)
        vision_path.write_text(vision_content, encoding="utf-8")

    # .gitignore
    _update_gitignore(project_root)

    # 总结
    typer.echo(f"\n  初始化完成！")
    typer.echo(f"  .agents/config.toml  已生成")
    if not launch_vision and vision_path.exists():
        typer.echo(f"  .agents/vision.md    已生成")
    typer.echo(f"  .gitignore           已更新")
    typer.echo(f"\n  运行 harness auto 开始自治开发")
    typer.echo(f"  运行 harness status 查看状态")

    # 衔接 harness vision
    if launch_vision:
        typer.echo("\n  -> 启动 harness vision...\n")
        from harness.commands.vision_cmd import run_vision
        run_vision()


def _update_gitignore(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    marker = ".agents/state.json"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if marker not in content:
            with gitignore.open("a", encoding="utf-8") as f:
                f.write("\n# harness — 不跟踪运行时状态\n")
                f.write(".agents/state.json\n")
                f.write(".agents/.stop\n")
    else:
        gitignore.write_text(
            "# harness — 不跟踪运行时状态\n.agents/state.json\n.agents/.stop\n",
            encoding="utf-8",
        )
