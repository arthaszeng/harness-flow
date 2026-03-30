"""项目扫描器 — 分析项目结构，发现 CI 相关配置并生成建议"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectScan:
    """项目扫描结果"""
    has_makefile: bool = False
    make_targets: list[str] = field(default_factory=list)
    has_pytest: bool = False
    pytest_dir: str = ""
    has_package_json: bool = False
    npm_scripts: list[str] = field(default_factory=list)
    has_pyproject: bool = False
    has_tox: bool = False
    has_architecture_check: bool = False
    suggested_commands: list[tuple[str, str]] = field(default_factory=list)


def scan_project(project_root: Path) -> ProjectScan:
    """扫描项目结构，返回 CI 相关发现"""
    scan = ProjectScan()

    _detect_makefile(project_root, scan)
    _detect_pytest(project_root, scan)
    _detect_npm(project_root, scan)
    _detect_pyproject(project_root, scan)
    _detect_tox(project_root, scan)
    _detect_architecture_check(project_root, scan)

    _build_suggestions(scan)
    return scan


def _detect_makefile(root: Path, scan: ProjectScan) -> None:
    makefile = root / "Makefile"
    if not makefile.exists():
        return
    scan.has_makefile = True
    content = makefile.read_text(encoding="utf-8", errors="ignore")

    # 解析 .PHONY targets
    for m in re.finditer(r"\.PHONY:\s*(.+)", content):
        targets = m.group(1).split()
        scan.make_targets.extend(targets)

    # 也解析独立 target 定义行（target: deps 形式）
    for m in re.finditer(r"^([a-zA-Z_][\w-]*):", content, re.MULTILINE):
        t = m.group(1)
        if t not in scan.make_targets:
            scan.make_targets.append(t)


def _detect_pytest(root: Path, scan: ProjectScan) -> None:
    for candidate in ["tests", "test"]:
        d = root / candidate
        if d.is_dir():
            scan.has_pytest = True
            scan.pytest_dir = candidate
            return

    if (root / "pytest.ini").exists() or (root / "conftest.py").exists():
        scan.has_pytest = True


def _detect_npm(root: Path, scan: ProjectScan) -> None:
    pkg = root / "package.json"
    if not pkg.exists():
        # 检查 frontend/ 子目录
        pkg = root / "frontend" / "package.json"
    if not pkg.exists():
        return

    scan.has_package_json = True
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        scan.npm_scripts = list(scripts.keys())
    except (json.JSONDecodeError, OSError):
        pass


def _detect_pyproject(root: Path, scan: ProjectScan) -> None:
    scan.has_pyproject = (root / "pyproject.toml").exists()


def _detect_tox(root: Path, scan: ProjectScan) -> None:
    scan.has_tox = (root / "tox.ini").exists()


def _detect_architecture_check(root: Path, scan: ProjectScan) -> None:
    for candidate in [
        root / "scripts" / "check_architecture.py",
        root / "scripts" / "check_arch.py",
        root / "tools" / "check_architecture.py",
    ]:
        if candidate.exists():
            scan.has_architecture_check = True
            return


def _build_suggestions(scan: ProjectScan) -> None:
    """根据扫描结果生成 CI 命令建议，按推荐度排序"""
    suggestions: list[tuple[int, str, str]] = []  # (priority, command, description)

    targets = set(scan.make_targets)

    if scan.has_makefile:
        # make check test（架构+测试）是最佳组合
        if "check" in targets and "test" in targets:
            suggestions.append((10, "make check test", "架构检查 + 单元测试"))
        # make ci 如果存在（可能包含 smoke，较重）
        if "ci" in targets:
            suggestions.append((5, "make ci", "完整 CI（可能含冒烟测试，较慢）"))
        # 单独 make test
        if "test" in targets and not ("check" in targets):
            suggestions.append((8, "make test", "单元测试"))
        elif "test" in targets:
            suggestions.append((6, "make test", "仅单元测试"))
        # make lint
        if "lint" in targets:
            suggestions.append((4, "make lint", "代码检查"))

    if scan.has_pytest:
        dir_arg = f" {scan.pytest_dir}/" if scan.pytest_dir else ""
        suggestions.append((3, f"python -m pytest{dir_arg} -v", "pytest 直接运行"))

    if scan.has_tox:
        suggestions.append((2, "tox", "tox 测试"))

    # 按 priority 降序排列
    suggestions.sort(key=lambda x: -x[0])
    scan.suggested_commands = [(cmd, desc) for _, cmd, desc in suggestions]


def format_scan_report(scan: ProjectScan) -> list[str]:
    """格式化扫描发现为展示行"""
    lines: list[str] = []
    if scan.has_makefile:
        relevant = [t for t in scan.make_targets if t in {
            "test", "check", "ci", "lint", "smoke", "smoke-backend", "smoke-frontend",
        }]
        if relevant:
            lines.append(f"Makefile (targets: {', '.join(relevant)})")
        else:
            lines.append("Makefile")

    if scan.has_pytest:
        lines.append(f"pytest ({scan.pytest_dir}/)" if scan.pytest_dir else "pytest")

    if scan.has_architecture_check:
        lines.append("scripts/check_architecture.py")

    if scan.has_package_json:
        relevant = [s for s in scan.npm_scripts if s in {"test", "lint", "build"}]
        if relevant:
            lines.append(f"package.json (scripts: {', '.join(relevant)})")
        else:
            lines.append("package.json")

    if scan.has_pyproject:
        lines.append("pyproject.toml")

    if scan.has_tox:
        lines.append("tox.ini")

    return lines
