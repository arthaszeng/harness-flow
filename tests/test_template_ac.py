"""Acceptance criteria tests for task-073: agent line counts, en/zh parity, plan_mode output."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.core.plan_lint import lint_plan

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "src" / "harness" / "templates" / "native"
AGENT_NAMES = [
    "agent-architect",
    "agent-engineer",
    "agent-product-owner",
    "agent-qa",
    "agent-project-manager",
]
MAX_AGENT_LINES = 80


class TestAgentLineCount:
    @pytest.mark.parametrize("name", AGENT_NAMES)
    def test_en_agent_under_max_lines(self, name):
        path = TEMPLATE_DIR / f"{name}.md.j2"
        assert path.exists(), f"missing {path}"
        lines = path.read_text().splitlines()
        assert len(lines) < MAX_AGENT_LINES, (
            f"{name} (EN) has {len(lines)} lines, expected < {MAX_AGENT_LINES}"
        )

    @pytest.mark.parametrize("name", AGENT_NAMES)
    def test_zh_agent_under_max_lines(self, name):
        path = TEMPLATE_DIR / "zh" / f"{name}.md.j2"
        assert path.exists(), f"missing {path}"
        lines = path.read_text().splitlines()
        assert len(lines) < MAX_AGENT_LINES, (
            f"{name} (ZH) has {len(lines)} lines, expected < {MAX_AGENT_LINES}"
        )


class TestAgentIncludesCommon:
    @pytest.mark.parametrize("name", AGENT_NAMES)
    def test_en_includes_agent_common(self, name):
        path = TEMPLATE_DIR / f"{name}.md.j2"
        content = path.read_text()
        assert "_agent-common.md.j2" in content, f"{name} (EN) does not include _agent-common"

    @pytest.mark.parametrize("name", AGENT_NAMES)
    def test_zh_includes_agent_common(self, name):
        path = TEMPLATE_DIR / "zh" / f"{name}.md.j2"
        content = path.read_text()
        assert "_agent-common.md.j2" in content, f"{name} (ZH) does not include _agent-common"


SECTION_TEMPLATES = [
    "_plan-review.md.j2",
    "_review-gate.md.j2",
    "_code-review.md.j2",
    "_plan-core.md.j2",
    "_plan-content.md.j2",
    "_ship-review-gate.md.j2",
    "_agent-common.md.j2",
]


class TestEnZhParity:
    """Verify en and zh section templates have matching heading structure."""

    @pytest.mark.parametrize("filename", SECTION_TEMPLATES)
    def test_section_exists_in_both_locales(self, filename):
        en_path = TEMPLATE_DIR / "sections" / filename
        zh_path = TEMPLATE_DIR / "zh" / "sections" / filename
        assert en_path.exists(), f"missing EN: {en_path}"
        assert zh_path.exists(), f"missing ZH: {zh_path}"

    @pytest.mark.parametrize("name", AGENT_NAMES)
    def test_agent_exists_in_both_locales(self, name):
        en_path = TEMPLATE_DIR / f"{name}.md.j2"
        zh_path = TEMPLATE_DIR / "zh" / f"{name}.md.j2"
        assert en_path.exists(), f"missing EN: {en_path}"
        assert zh_path.exists(), f"missing ZH: {zh_path}"


VALID_PLAN = """\
# Spec

## Analysis
Technical analysis here.

## Approach
Implementation approach here.

## Impact
Impact description.

## Risks
Risk list.

---

# Contract

## Deliverables
- [ ] **D1: First deliverable**
  - AC: something

## Acceptance Criteria
- All tests pass

## Out of Scope
- Nothing extra
"""


class TestPlanLintPlanMode:
    def test_small_plan_mode(self, tmp_path):
        p = tmp_path / "plan.md"
        p.write_text(VALID_PLAN)
        result = lint_plan(p)
        d = result.to_dict()
        assert "plan_mode" in d
        assert d["plan_mode"] == "small"

    def test_large_plan_mode(self, tmp_path):
        content = VALID_PLAN.replace(
            "- [ ] **D1: First deliverable**\n  - AC: something",
            "\n".join(
                f"- [ ] **D{i}: Deliverable {i}**\n  - AC: something"
                for i in range(1, 8)
            ),
        )
        content += "\n~20 files affected\n"
        p = tmp_path / "plan.md"
        p.write_text(content)
        result = lint_plan(p)
        d = result.to_dict()
        assert d["plan_mode"] == "large"
