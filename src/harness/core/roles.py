"""Role registry — single source of truth for all agent roles.

Dependency graph:
    roles.py ──> config.py      (KNOWN_MODEL_ROLES validation)
             ──> resolver.py    (ROLE_AGENT_MAP routing)
             ──> install.py     (agent file mapping)
             ──> workflow.py    (phase orchestration)
             ──> tests          (agent definition validation)

Zero side effects. Safe to import from build scripts, tests, and runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowPhase(Enum):
    PLANNING = "planning"
    CONTRACTED = "contracted"
    BUILDING = "building"
    EVALUATING = "evaluating"
    DONE = "done"
    BLOCKED = "blocked"


class RoleCapability(Enum):
    READONLY = "readonly"
    READWRITE = "readwrite"


@dataclass(frozen=True)
class RoleDescriptor:
    name: str
    agent_name: str
    capability: RoleCapability
    description: str
    phases: tuple[WorkflowPhase, ...]


ROLE_REGISTRY: dict[str, RoleDescriptor] = {
    "planner": RoleDescriptor(
        name="planner",
        agent_name="harness-planner",
        capability=RoleCapability.READONLY,
        description="Analyzes requirements and produces spec + contract",
        phases=(WorkflowPhase.PLANNING,),
    ),
    "builder": RoleDescriptor(
        name="builder",
        agent_name="harness-builder",
        capability=RoleCapability.READWRITE,
        description="Implements contract deliverables",
        phases=(WorkflowPhase.BUILDING,),
    ),
    "evaluator": RoleDescriptor(
        name="evaluator",
        agent_name="harness-evaluator",
        capability=RoleCapability.READONLY,
        description="Reviews builder output and scores on four dimensions",
        phases=(WorkflowPhase.EVALUATING,),
    ),
    "alignment_evaluator": RoleDescriptor(
        name="alignment_evaluator",
        agent_name="harness-alignment-evaluator",
        capability=RoleCapability.READONLY,
        description="Checks implementation alignment with original requirement",
        phases=(WorkflowPhase.EVALUATING,),
    ),
    "strategist": RoleDescriptor(
        name="strategist",
        agent_name="harness-strategist",
        capability=RoleCapability.READONLY,
        description="Decides the next task in autonomous mode",
        phases=(),
    ),
    "reflector": RoleDescriptor(
        name="reflector",
        agent_name="harness-reflector",
        capability=RoleCapability.READONLY,
        description="Summarizes progress and spots patterns",
        phases=(),
    ),
    "advisor": RoleDescriptor(
        name="advisor",
        agent_name="harness-advisor",
        capability=RoleCapability.READONLY,
        description="Expands user input into structured vision",
        phases=(),
    ),
}

ALL_ROLES: frozenset[str] = frozenset(ROLE_REGISTRY.keys())
ALL_AGENT_NAMES: frozenset[str] = frozenset(
    r.agent_name for r in ROLE_REGISTRY.values()
)

SCORING_DIMENSIONS: tuple[str, ...] = (
    "completeness",
    "quality",
    "regression",
    "design",
)

EVALUATION_VERDICTS: frozenset[str] = frozenset({"PASS", "ITERATE", "CI_FAIL"})
ALIGNMENT_VERDICTS: frozenset[str] = frozenset({"ALIGNED", "MISALIGNED", "CONTRACT_ISSUE"})


def get_role(name: str) -> RoleDescriptor:
    """Look up a role descriptor; raises KeyError if unknown."""
    return ROLE_REGISTRY[name]


def get_agent_name(role: str) -> str:
    """Return the agent name for a role."""
    return ROLE_REGISTRY[role].agent_name


# ---------------------------------------------------------------------------
# Load-time consistency checks (fail fast on import if registry drifts)
# ---------------------------------------------------------------------------

def _validate_registry() -> None:
    """Cross-check the registry for internal consistency."""
    names = set()
    agent_names = set()
    for role, desc in ROLE_REGISTRY.items():
        if role != desc.name:
            raise RuntimeError(
                f"ROLE_REGISTRY key '{role}' != descriptor name '{desc.name}'"
            )
        if desc.agent_name in agent_names:
            raise RuntimeError(
                f"Duplicate agent_name '{desc.agent_name}' in ROLE_REGISTRY"
            )
        if not desc.agent_name.startswith("harness-"):
            raise RuntimeError(
                f"Agent name '{desc.agent_name}' does not follow 'harness-' convention"
            )
        names.add(role)
        agent_names.add(desc.agent_name)


_validate_registry()
