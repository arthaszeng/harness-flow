"""Declarative artifact dependency graph for task workflows.

Defines the standard set of task artifacts, their file patterns,
dependencies, and optional validators. Provides pure-function status
computation: given a task directory's files and artifact definitions,
determine which artifacts are done/ready/blocked/missing/invalid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from harness.core.gates import (
    BUILD_ROUND_RE,
    CODE_EVAL_ROUND_RE,
    LEGACY_BUILD_ROUND_RE,
    LEGACY_EVAL_ROUND_RE,
)


class ArtifactStatus(str, Enum):
    DONE = "done"
    READY = "ready"
    BLOCKED = "blocked"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(frozen=True)
class ArtifactDef:
    """Declarative definition of a task artifact."""

    id: str
    description: str
    file_patterns: tuple[re.Pattern[str], ...]
    requires: tuple[str, ...] = ()
    validator: str | None = None
    is_round_numbered: bool = False

    def find_file(self, task_dir: Path) -> Path | None:
        """Find the matching file in task_dir. For round-numbered artifacts,
        returns the file with the highest round number."""
        if not task_dir.exists():
            return None
        best: tuple[int, Path] | None = None
        try:
            entries = list(task_dir.iterdir())
        except OSError:
            return None

        for entry in entries:
            if not entry.is_file():
                continue
            for pattern in self.file_patterns:
                m = pattern.search(entry.name)
                if m:
                    if self.is_round_numbered:
                        try:
                            num = int(m.group(1))
                        except (IndexError, ValueError):
                            num = 0
                        if best is None or num > best[0]:
                            best = (num, entry)
                    else:
                        return entry
                    break
        return best[1] if best else None

    def file_exists(self, task_dir: Path) -> bool:
        """Check if the artifact file exists and has non-whitespace content."""
        found = self.find_file(task_dir)
        if found is None:
            return False
        try:
            size = found.stat().st_size
            if size == 0:
                return False
            with open(found, "rb") as f:
                head = f.read(64)
            return bool(head.strip())
        except OSError:
            return False


_PLAN_EVAL_ROUND_RE = re.compile(r"plan-eval-r(\d+)\.md$")
_HANDOFF_PLAN_RE = re.compile(r"^handoff-plan\.json$")
_HANDOFF_BUILD_RE = re.compile(r"^handoff-build\.json$")
_SHIP_METRICS_RE = re.compile(r"^ship-metrics\.json$")
_FEEDBACK_LEDGER_RE = re.compile(r"^feedback-ledger\.jsonl$")
_FAILURE_PATTERNS_RE = re.compile(r"^failure-patterns\.jsonl$")
_PLAN_RE = re.compile(r"^plan\.md$")


STANDARD_ARTIFACTS: tuple[ArtifactDef, ...] = (
    ArtifactDef(
        id="plan",
        description="Task plan with spec and contract",
        file_patterns=(_PLAN_RE,),
        requires=(),
        validator="plan-lint",
    ),
    ArtifactDef(
        id="plan-eval",
        description="Plan evaluation (multi-role review result)",
        file_patterns=(_PLAN_EVAL_ROUND_RE,),
        requires=("plan",),
        is_round_numbered=True,
    ),
    ArtifactDef(
        id="handoff-plan",
        description="Structured handoff from plan to build phase",
        file_patterns=(_HANDOFF_PLAN_RE,),
        requires=("plan",),
    ),
    ArtifactDef(
        id="build-log",
        description="Build round log (implementation record)",
        file_patterns=(BUILD_ROUND_RE, LEGACY_BUILD_ROUND_RE),
        requires=("plan",),
        is_round_numbered=True,
    ),
    ArtifactDef(
        id="handoff-build",
        description="Structured handoff from build to ship phase",
        file_patterns=(_HANDOFF_BUILD_RE,),
        requires=("build-log",),
    ),
    ArtifactDef(
        id="code-eval",
        description="Code evaluation (multi-role review result)",
        file_patterns=(CODE_EVAL_ROUND_RE, LEGACY_EVAL_ROUND_RE),
        requires=("build-log",),
        is_round_numbered=True,
    ),
    ArtifactDef(
        id="ship-metrics",
        description="Ship metrics (quality, efficiency, coverage)",
        file_patterns=(_SHIP_METRICS_RE,),
        requires=("code-eval",),
    ),
    ArtifactDef(
        id="feedback-ledger",
        description="Per-round feedback and learning ledger",
        file_patterns=(_FEEDBACK_LEDGER_RE,),
        requires=("code-eval",),
    ),
    ArtifactDef(
        id="failure-patterns",
        description="Extracted failure patterns for future prevention",
        file_patterns=(_FAILURE_PATTERNS_RE,),
        requires=("code-eval",),
    ),
)

ARTIFACT_BY_ID: dict[str, ArtifactDef] = {a.id: a for a in STANDARD_ARTIFACTS}


@dataclass
class ArtifactInfo:
    """Status of a single artifact in a specific task directory."""

    id: str
    status: ArtifactStatus
    file_path: str | None = None
    description: str = ""
    requires: tuple[str, ...] = ()
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "status": self.status.value,
            "description": self.description,
        }
        if self.file_path:
            d["file_path"] = self.file_path
        if self.requires:
            d["requires"] = list(self.requires)
        if self.validation_errors:
            d["validation_errors"] = self.validation_errors
        return d


@dataclass
class TaskArtifactReport:
    """Complete artifact status report for a task directory."""

    task_id: str
    artifacts: list[ArtifactInfo]
    next_actions: list[str]

    @property
    def done_ids(self) -> set[str]:
        return {a.id for a in self.artifacts if a.status == ArtifactStatus.DONE}

    @property
    def ready_ids(self) -> set[str]:
        return {a.id for a in self.artifacts if a.status == ArtifactStatus.READY}

    @property
    def blocked_ids(self) -> set[str]:
        return {a.id for a in self.artifacts if a.status == ArtifactStatus.BLOCKED}

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "summary": {
                "done": sorted(self.done_ids),
                "ready": sorted(self.ready_ids),
                "blocked": sorted(self.blocked_ids),
            },
            "next_actions": self.next_actions,
        }


ValidatorFunc = Callable[[Path, ArtifactDef], list[str]]


def _run_plan_lint_validator(task_dir: Path, artifact_def: ArtifactDef) -> list[str]:
    """Run plan-lint and return error messages."""
    from harness.core.plan_lint import lint_plan

    plan_path = task_dir / "plan.md"
    result = lint_plan(plan_path)
    return [e.message for e in result.errors]


_VALIDATORS: dict[str, ValidatorFunc] = {
    "plan-lint": _run_plan_lint_validator,
}


def compute_artifact_report(
    task_dir: Path,
    artifact_defs: tuple[ArtifactDef, ...] = STANDARD_ARTIFACTS,
    *,
    validators: dict[str, ValidatorFunc] | None = None,
) -> TaskArtifactReport:
    """Compute the status of all artifacts for a task directory.

    Pure function: reads only from the filesystem (file existence/content),
    does not modify any state.
    """
    if validators is None:
        validators = _VALIDATORS

    done_set: set[str] = set()
    infos: list[ArtifactInfo] = []

    for adef in artifact_defs:
        exists = adef.file_exists(task_dir)
        found = adef.find_file(task_dir) if exists else None

        if exists:
            validation_errors: list[str] = []
            if adef.validator and adef.validator in validators:
                validation_errors = validators[adef.validator](task_dir, adef)

            if validation_errors:
                status = ArtifactStatus.INVALID
            else:
                status = ArtifactStatus.DONE
                done_set.add(adef.id)

            infos.append(ArtifactInfo(
                id=adef.id,
                status=status,
                file_path=found.name if found else None,
                description=adef.description,
                requires=adef.requires,
                validation_errors=validation_errors,
            ))
        else:
            deps_met = all(dep in done_set for dep in adef.requires)
            status = ArtifactStatus.READY if deps_met else ArtifactStatus.BLOCKED

            infos.append(ArtifactInfo(
                id=adef.id,
                status=status,
                description=adef.description,
                requires=adef.requires,
            ))

    next_actions = suggest_next_actions(infos)
    return TaskArtifactReport(
        task_id=task_dir.name,
        artifacts=infos,
        next_actions=next_actions,
    )


_ACTION_MAP: dict[str, str] = {
    "plan": "Create task plan (run /harness-plan)",
    "plan-eval": "Run plan evaluation (multi-role review)",
    "handoff-plan": "Write plan-to-build handoff (harness handoff write)",
    "build-log": "Implement the plan (run /harness-build)",
    "handoff-build": "Write build-to-ship handoff",
    "code-eval": "Run code evaluation (multi-role code review)",
    "ship-metrics": "Complete ship pipeline (run /harness-ship)",
    "feedback-ledger": "Write feedback ledger entry",
    "failure-patterns": "Extract failure patterns if applicable",
}


def suggest_next_actions(artifacts: list[ArtifactInfo]) -> list[str]:
    """Suggest next actions based on artifact statuses.

    Returns actions for artifacts that are READY (dependencies met but
    artifact not yet created).  Prioritizes the critical path:
    plan → build-log → code-eval → ship-metrics.
    """
    ready = [a for a in artifacts if a.status == ArtifactStatus.READY]
    invalid = [a for a in artifacts if a.status == ArtifactStatus.INVALID]

    actions: list[str] = []

    for a in invalid:
        errors = ", ".join(a.validation_errors[:3])
        actions.append(f"Fix {a.id}: {errors}")

    critical_path = ["plan", "build-log", "code-eval", "ship-metrics"]
    seen = set()
    for crit_id in critical_path:
        for a in ready:
            if a.id == crit_id and a.id not in seen:
                action = _ACTION_MAP.get(a.id, f"Create {a.id}")
                actions.append(action)
                seen.add(a.id)
                break

    for a in ready:
        if a.id not in seen:
            action = _ACTION_MAP.get(a.id, f"Create {a.id}")
            actions.append(action)
            seen.add(a.id)

    return actions


def generate_resume_context(task_dir: Path) -> str:
    """Generate a concise resume context from artifact completion state.

    Returns a multi-line string (max ~500 chars) suitable for agent
    context injection at session start. Combines artifact status with
    workflow phase (if available) and next-step suggestions.
    """
    report = compute_artifact_report(task_dir, validators={})

    done = [a.id for a in report.artifacts if a.status == ArtifactStatus.DONE]
    invalid = [a.id for a in report.artifacts if a.status == ArtifactStatus.INVALID]

    lines: list[str] = [f"Task: {report.task_id}"]

    phase_str = _read_workflow_phase(task_dir)
    if phase_str:
        lines.append(f"Phase: {phase_str}")

    if done:
        lines.append(f"Done: {', '.join(done)}")
    if invalid:
        lines.append(f"Invalid: {', '.join(invalid)}")

    if report.next_actions:
        lines.append(f"Next: {report.next_actions[0]}")

    return "\n".join(lines)


def _read_workflow_phase(task_dir: Path) -> str:
    """Best-effort read of workflow phase from workflow-state.json."""
    import json

    ws_path = task_dir / "workflow-state.json"
    if not ws_path.exists():
        return ""
    try:
        raw = json.loads(ws_path.read_text(encoding="utf-8"))
        return raw.get("phase", "")
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return ""
