# Architecture

This document explains **why** harness-orchestrator is designed the way it is. For **what** each module does, read the code and docstrings. For **how** to use it, see README.md.

## Core Design: GAN-style Builder vs Evaluator

The central insight is borrowed from Generative Adversarial Networks: a **Builder** (generator) produces code while an **Evaluator** (discriminator) reviews it. The **Planner** acts as the shared latent space — both Builder and Evaluator work from the same Spec + Contract.

```
Requirement
    │
    ▼
┌──────────┐     Spec + Contract     ┌──────────┐
│  Planner │ ────────────────────────►│  Builder  │
│ (readonly)│                          │(readwrite)│
└──────────┘                          └─────┬─────┘
    ▲                                       │ code changes
    │ feedback                              ▼
┌──────────┐     score + verdict     ┌──────────┐
│  Planner │ ◄───────────────────────│ Evaluator│
│  (re-plan)│                         │(readonly) │
└──────────┘                          └──────────┘
```

This adversarial loop continues until the Evaluator passes the work or max iterations are reached. The key property: **the Builder cannot grade its own work**.

### Why this works

- **Separation of concerns**: Planner thinks about design, Builder writes code, Evaluator judges quality. No single agent has all permissions and responsibilities.
- **Iterative refinement**: Evaluator feedback flows to Planner, not directly to Builder. This forces structural fixes rather than superficial patches.
- **Trust boundaries**: Builder output is explicitly marked as untrusted in Evaluator prompts, preventing rubber-stamp approvals.

## State Machine

Task progression follows a strict transition graph (see `core/state.py`):

```
IDLE → PLANNING → CONTRACTED → BUILDING → EVALUATING
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                                  DONE      PLANNING   BLOCKED
                                   │       (re-iterate)   │
                                   ▼                      ▼
                                  IDLE                   IDLE
```

Every transition is validated at runtime — illegal transitions raise `RuntimeError`. State is checkpointed to `.agents/state.json` on every transition, enabling resume after interruption.

## Role Registry (SSOT)

`core/roles.py` is the single source of truth for all agent roles. It serves:

- **Runtime**: role → agent name lookup, capability checks
- **Configuration**: `KNOWN_MODEL_ROLES` for config validation
- **Routing**: `ROLE_AGENT_MAP` for driver resolution
- **Tests**: agent definition file validation

The registry runs load-time consistency checks on import — duplicate agent names, naming convention violations, or key/name mismatches raise immediately rather than failing at runtime.

## Driver Abstraction

`AgentDriver` is a Protocol (structural typing) with two implementations:

- **CursorDriver**: invokes `cursor-agent` CLI
- **CodexDriver**: invokes `codex exec` CLI

`DriverResolver` routes roles to drivers based on config:
- `auto` mode: Builder → Cursor (better for code edits), others → Codex (better for analysis)
- Per-role overrides available in config
- Probes at startup detect which CLIs are functional

The driver abstraction means adding a new IDE backend (e.g., Windsurf, Kiro) requires only implementing `invoke()`, `is_available()`, and `probe()`.

## Error Translation Layer

Inspired by gstack's `wrapError()`, the `methodology/error_hints.py` module translates raw CI/builder output into structured feedback for the next iteration:

1. **Classify**: regex-based pattern matching categorizes errors (syntax, test failure, lint, timeout, etc.)
2. **Extract**: key error lines are pulled from verbose output
3. **Suggest**: each category maps to an actionable next-step suggestion
4. **Format**: structured Markdown with category, key lines, suggestion, and truncated raw output

The design principle: **error messages target AI agents, not human developers**. An agent needs "Fix the syntax error at line 42 in foo.py" more than a full stack trace.

## Configuration Cascade

Config is loaded from TOML with cascading precedence:

```
~/.harness/config.toml  (global defaults)
       ▼  deep merge
.agents/config.toml     (project overrides — wins)
       ▼  Pydantic validation
HarnessConfig           (runtime object)
```

Model resolution follows its own cascade: `role_overrides[role]` → `role_configs[role].model` → `driver_defaults[driver]` → `default`. Empty string means "use IDE default model."

## Autonomous Mode

The autonomous loop adds two more roles around the single-task workflow:

- **Strategist**: picks the next task from the vision
- **Reflector**: periodically summarizes progress and detects vision drift

Safety valves prevent runaway execution:
- `.agents/.stop` file (graceful stop signal)
- `max_tasks_per_session` cap
- Consecutive blocked circuit breaker

## Artifact Layout

All artifacts live under `.agents/` in the target project:

```
.agents/
├── config.toml          # Project configuration
├── state.json           # State machine checkpoint (gitignored)
├── vision.md            # Project vision
├── progress.md          # Task history
├── .stop                # Graceful stop signal (gitignored)
├── tasks/
│   └── task-001/
│       ├── spec-r1.md
│       ├── contract-r1.md
│       ├── contract-r1.json    # Machine-readable sidecar
│       ├── build-r1.log
│       ├── evaluation-r1.md
│       ├── evaluation-r1.json  # Machine-readable sidecar
│       └── insights.json
├── archive/             # Completed tasks moved here
│   └── task-001/
└── runs/
    └── <session-id>/
        └── events.jsonl  # Append-only event log
```

## Testing Philosophy

Tests are organized by cost and scope:

- **Unit tests** (`test_config`, `test_state`, `test_scoring`): fast, no I/O, test pure logic
- **Integration tests** (`test_workflow`): use tmp git repos with mocked drivers — verify the full plan→build→eval loop without real LLM calls
- **Definition tests** (`test_agent_definitions`): static validation that agent files, install mappings, role registries, and localization stay in sync — inspired by gstack's skill-validation approach

The key testing principle: **agent definition files are executable documentation**. If they drift from the code, tests catch it before runtime does.

## i18n

Lightweight module-level catalogs (`i18n/en.py`, `i18n/zh.py`) with `t(key, **kwargs)` lookup. Falls back to English if a key is missing in the current language. Prompts are fully localized so agents receive instructions in the project's configured language.

## Design Decisions Log

### Why contracts instead of free-form prompts?

Contracts give the Evaluator a concrete checklist to score against. Without them, evaluation becomes subjective and scores drift. The Planner adjusts contracts between iterations based on feedback, so they evolve without losing structure.

### Why rebase-and-merge instead of merge commits?

Linear history makes it easy to see what each task added. The task branch is deleted after merge, keeping the branch list clean. If rebase fails (conflicts), the branch is preserved for manual resolution.

### Why shortest-plank weighting for scores?

A task that scores 5/5/5/1 (great code quality but broken tests) should not pass. The weighted score pulls toward the minimum dimension, ensuring all four quality aspects meet the threshold.

### Why separate Planner and Builder roles?

The Builder has write access to the codebase. If it also planned, it could rationalize scope creep or skip design thinking. Separation forces the plan to be reviewed (by the Evaluator) independently of who wrote the code.
