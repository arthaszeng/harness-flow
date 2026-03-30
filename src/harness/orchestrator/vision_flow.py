"""Vision 生成编排 — Advisor 驱动的 vision 创建/更新"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from harness.drivers.base import AgentDriver


@dataclass
class ProjectContext:
    """收集到的项目上下文"""
    project_name: str = ""
    existing_vision: str = ""
    reflection: str = ""
    progress: str = ""
    doc_summaries: list[str] = field(default_factory=list)
    directory_tree: str = ""


@dataclass
class AdvisorOutput:
    """Advisor agent 的解析结果"""
    vision_content: str
    questions: list[str] = field(default_factory=list)


def gather_context(project_root: Path) -> ProjectContext:
    """收集项目上下文供 Advisor 使用"""
    agents_dir = project_root / ".agents"
    ctx = ProjectContext()

    ctx.project_name = project_root.name

    # 现有 vision
    vision_path = agents_dir / "vision.md"
    if vision_path.exists():
        ctx.existing_vision = vision_path.read_text(encoding="utf-8")[:3000]

    # Reflector 反思
    reflection_path = agents_dir / "reflection.md"
    if reflection_path.exists():
        ctx.reflection = reflection_path.read_text(encoding="utf-8")[:3000]

    # 进展
    progress_path = agents_dir / "progress.md"
    if progress_path.exists():
        ctx.progress = progress_path.read_text(encoding="utf-8")[:3000]

    # doc/ 下的文档摘要
    doc_dir = project_root / "doc"
    if doc_dir.is_dir():
        for md_file in sorted(doc_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")[:2000]
            ctx.doc_summaries.append(f"### {md_file.name}\n{content}")

    # 目录结构（浅层）
    ctx.directory_tree = _get_directory_tree(project_root)

    return ctx


def build_advisor_prompt(ctx: ProjectContext, user_input: str) -> str:
    """组装 Advisor prompt"""
    sections: list[str] = []

    sections.append(f"## 项目名称\n{ctx.project_name}")
    sections.append(f"## 用户需求\n{user_input}")

    if ctx.existing_vision:
        sections.append(f"## 现有 Vision\n{ctx.existing_vision}")

    if ctx.progress:
        sections.append(f"## 已完成的工作\n{ctx.progress}")

    if ctx.reflection:
        sections.append(f"## Reflector 反思\n{ctx.reflection}")

    if ctx.doc_summaries:
        docs = "\n\n".join(ctx.doc_summaries[:3])
        sections.append(f"## 项目文档摘要\n{docs}")

    if ctx.directory_tree:
        sections.append(f"## 项目结构\n```\n{ctx.directory_tree}\n```")

    sections.append(
        "请根据以上上下文，将用户需求展开为结构化的项目愿景。"
        "严格按照你的指令中定义的四段式格式输出。"
    )

    return "\n\n".join(sections)


def invoke_advisor(
    driver: AgentDriver,
    agent_name: str,
    ctx: ProjectContext,
    user_input: str,
    cwd: Path,
    *,
    timeout: int = 300,
    on_output: Callable[[str], None] | None = None,
) -> AdvisorOutput:
    """调用 Advisor agent，返回解析后的结果"""
    prompt = build_advisor_prompt(ctx, user_input)
    result = driver.invoke(
        agent_name, prompt, cwd, readonly=True, timeout=timeout, on_output=on_output,
    )

    if not result.success:
        return AdvisorOutput(
            vision_content="",
            questions=["Advisor 调用失败，请重试。"],
        )

    return parse_advisor_output(result.output)


def parse_advisor_output(output: str) -> AdvisorOutput:
    """解析 Advisor 输出，分离 vision 和追问"""
    questions: list[str] = []
    vision_content = output.strip()

    # 分离追问部分
    marker = "ADVISOR_QUESTIONS:"
    if marker in output:
        parts = output.split(marker, 1)
        vision_content = parts[0].strip()
        q_section = parts[1].strip()
        for line in q_section.split("\n"):
            line = line.strip()
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            if cleaned:
                questions.append(cleaned)

    return AdvisorOutput(vision_content=vision_content, questions=questions)


def write_vision(agents_dir: Path, content: str) -> int:
    """写入 vision.md，返回写入字节数"""
    vision_path = agents_dir / "vision.md"
    vision_path.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def _get_directory_tree(project_root: Path, max_depth: int = 2) -> str:
    """获取项目目录结构（排除常见噪声目录）"""
    try:
        result = subprocess.run(
            [
                "find", str(project_root),
                "-maxdepth", str(max_depth),
                "-type", "d",
                "-not", "-path", "*/.git/*",
                "-not", "-path", "*/__pycache__/*",
                "-not", "-path", "*/node_modules/*",
                "-not", "-path", "*/.next/*",
                "-not", "-path", "*/.agents/tasks/*",
                "-not", "-path", "*/.agents/archive/*",
                "-not", "-name", ".git",
                "-not", "-name", "__pycache__",
                "-not", "-name", "node_modules",
                "-not", "-name", ".next",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            # 转为相对路径
            rel = []
            for line in lines:
                p = Path(line)
                try:
                    rel.append(str(p.relative_to(project_root)))
                except ValueError:
                    rel.append(line)
            return "\n".join(sorted(rel))[:1500]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # fallback: 手动遍历
    dirs = []
    for p in sorted(project_root.iterdir()):
        if p.is_dir() and not p.name.startswith(".") and p.name not in {
            "__pycache__", "node_modules", ".next",
        }:
            dirs.append(p.name + "/")
    return "\n".join(dirs)[:1500]
