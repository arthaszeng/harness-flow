[中文](README.zh-CN.md)

# harness-orchestrator

> Cursor-native multi-agent development framework — run a full plan-build-review-ship pipeline inside Cursor with one command.

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

AI coding tools excel at single-shot tasks. Continuous development needs more: goal tracking, quality gates, adversarial review, and audit trails. Harness organizes these into a contract-driven engineering loop that runs **inside your Cursor IDE** — no separate orchestrator process, no complex setup.

## Upgrading from 3.x

Version 4.0.0 removes orchestrator mode entirely. If you used `harness run`, `harness auto`, `harness stop`, or `harness vision`, these CLI commands no longer exist.

**Migration path:**
- `harness run <req>` → Use `/harness-plan <req>` in Cursor IDE
- `harness auto` → Use `/harness-vision` in Cursor IDE
- `harness vision` → Use `/harness-vision` in Cursor IDE
- `harness stop` → Not needed (Cursor IDE manages task lifecycle)
- `[drivers]` config section → Ignored (safe to leave in config)
- `[autonomous]` config section → Removed (native mode has no autonomous loop)
- `models.driver_defaults` → Removed (no drivers in native mode)
- `workflow.mode` → Removed (always cursor-native)

Your `.agents/config.toml` will continue to load without errors — unknown sections are silently ignored.

---

## Quick Start (3 minutes)

### 1. Install harness

```bash
pip install harness-orchestrator
harness --version
```

<details>
<summary>Alternative: install from source (for contributors)</summary>

```bash
git clone https://github.com/arthaszeng/harness-orchestrator.git
cd harness-orchestrator
pip install -e ".[dev]"
```

</details>

### 2. Initialize your project

```bash
cd /path/to/your/project
harness init
```

The wizard walks you through setup: project info, trunk branch, CI command, and optional Memverse integration. It generates skills, subagents, and rules directly into your `.cursor/` directory.

### 3. Use it in Cursor

Open your project in Cursor. You now have **three primary entry points** that cover all task sizes:

| Skill | When to use | What it does |
|-------|-------------|--------------|
| `/harness-brainstorm` | "I have an idea" | Divergent exploration → vision → plan → review gate → auto build/eval/ship/retro |
| `/harness-vision` | "I have a direction" | Clarify vision → plan → review gate → auto build/eval/ship/retro |
| `/harness-plan` | "I have a requirement" | Refine plan + 5-role review → review gate → auto build/eval/ship/retro |

All three use recursive composition (brainstorm ⊃ vision ⊃ plan) and share the same plan review → ship pipeline.

**Utility skills:**

| Skill | What it does |
|-------|-------------|
| `/harness-investigate` | Systematic bug investigation: reproduce → hypothesize → verify → minimal fix |
| `/harness-learn` | Memverse knowledge management: store, retrieve, update project learnings |
| `/harness-retro` | Engineering retrospective: commit analytics, hotspot detection, trend tracking |

**Advanced skills** (for granular control):

| Skill | What it does |
|-------|-------------|
| `/harness-build` | Implement the contract, run CI, triage failures, write a structured build log |
| `/harness-eval` | 5-role code review (architect + product-owner + engineer + qa + project-manager) |
| `/harness-ship` | Full pipeline: test → review → fix → commit → push → PR |
| `/harness-doc-release` | Documentation sync: detect stale docs after code changes |

**Try it now** — open Cursor chat and type:

```
/harness-plan add input validation to the user registration endpoint
```

### Updating

```bash
harness update          # upgrade to latest, reinstall artifacts, check config
harness update --check  # just check if a new version is available
```

---

## What happens under the hood

```
You type /harness-ship "add feature X"
  → Rebase onto main, run tests
  → 5-role code evaluation (all dispatched in parallel):
      Architect:       design + security review
      Product Owner:   completeness + behavior
      Engineer:        quality + performance
      QA:              regression + testing (only role running CI)
      Project Manager: scope + delivery
  → Fix-First: auto-fix trivial issues, ask about important ones
  → Bisectable commits + push + PR
```

### Unified 5-role review system

The same 5 specialized roles review both **plans** and **code**, dispatched in parallel:

| Role | Plan Review Focus | Code Eval Focus |
|------|------------------|-----------------|
| **Architect** | Feasibility, module impact, dependency changes | Conformance, layering, coupling, security |
| **Product Owner** | Vision alignment, user value, acceptance criteria | Requirement coverage, behavioral correctness |
| **Engineer** | Implementation feasibility, code reuse, tech debt | Code quality, DRY, patterns, performance |
| **QA** | Test strategy, boundary values, regression risk | Test coverage, edge cases, CI health |
| **Project Manager** | Task decomposition, parallelism, scope | Scope drift, plan completion, delivery risk |

Findings from 2+ roles are flagged as **high confidence**. Each role can use a different model via `[native.role_models]` in `.agents/config.toml`.

### Fix-First auto-remediation

Review findings are classified before presenting:

- **AUTO-FIX** — High certainty, small blast radius, reversible. Fixed immediately and committed.
- **ASK** — Security findings, behavior changes, or low confidence. Presented to you for decision.

### Graceful degradation

| Roles responding | Behavior |
|-----------------|----------|
| 5/5 | Full synthesis with cross-validation |
| 3-4/5 | Proceed with available reviews, note missing perspectives |
| 1-2/5 | Log warning, fall through to single-agent review |
| 0/5 | Fall back to single generalPurpose subagent |

---

## Generated artifacts

`harness init` generates:

| Artifact | Path | Purpose |
|----------|------|---------|
| `/harness-brainstorm` | `.cursor/skills/harness/harness-brainstorm/SKILL.md` | Divergent exploration → vision → plan → auto-execute to PR |
| `/harness-vision` | `.cursor/skills/harness/harness-vision/SKILL.md` | Clarify vision → plan → auto-execute to PR |
| `/harness-plan` | `.cursor/skills/harness/harness-plan/SKILL.md` | Refine plan + 5-role review → auto-execute to PR |
| `/harness-build` | `.cursor/skills/harness/harness-build/SKILL.md` | Build: implement contract, run CI, triage failures |
| `/harness-eval` | `.cursor/skills/harness/harness-eval/SKILL.md` | 5-role code review with Fix-First auto-remediation |
| `/harness-ship` | `.cursor/skills/harness/harness-ship/SKILL.md` | Full pipeline: test → 5-role review → fix → commit → PR |
| `/harness-investigate` | `.cursor/skills/harness/harness-investigate/SKILL.md` | Systematic bug investigation and minimal fix |
| `/harness-learn` | `.cursor/skills/harness/harness-learn/SKILL.md` | Memverse knowledge management |
| `/harness-doc-release` | `.cursor/skills/harness/harness-doc-release/SKILL.md` | Documentation sync after code changes |
| `/harness-retro` | `.cursor/skills/harness/harness-retro/SKILL.md` | Engineering retrospective and trend analysis |
| Architect | `.cursor/agents/harness-architect.md` | Architecture reviewer (plan + code, dual-mode) |
| Product Owner | `.cursor/agents/harness-product-owner.md` | Product reviewer (plan + code, dual-mode) |
| Engineer | `.cursor/agents/harness-engineer.md` | Engineering reviewer (plan + code, dual-mode) |
| QA | `.cursor/agents/harness-qa.md` | QA reviewer with CI ownership (plan + code, dual-mode) |
| Project Manager | `.cursor/agents/harness-project-manager.md` | Delivery reviewer (plan + code, dual-mode) |
| Trust boundary | `.cursor/rules/harness-trust-boundary.mdc` | Always-on: Builder output is untrusted |
| Fix-First | `.cursor/rules/harness-fix-first.mdc` | Always-on: classify findings before presenting |
| Workflow conventions | `.cursor/rules/harness-workflow.mdc` | Commit format, branch naming, task state |
| Safety guardrails | `.cursor/rules/harness-safety-guardrails.mdc` | Always-on: destructive command detection and warning |
| Worktrees config | `.cursor/worktrees.json` | Parallel Agents: worktree init script for isolated checkouts |

To regenerate after config changes:

```bash
harness install --force
```

---

## Parallel Development

> **Key feature** — Run multiple harness tasks simultaneously without file conflicts.

When you run several Cursor agent tabs in the same project, they share one working directory.
Uncommitted changes from one task leak into another, causing confusion and broken builds.

Harness solves this automatically via **Cursor Parallel Agents** — each agent gets its own
isolated git worktree with a separate checkout. Cursor creates, uses, and cleans up these
worktrees transparently.

`harness init` generates `.cursor/worktrees.json`, which tells Cursor how to initialize
each worktree. After init, simply open multiple agent tabs in Cursor and start different tasks.

---

## Configuration

Project settings live in `.agents/config.toml`:

| Key | Default | Description |
|-----|---------|-------------|
| `workflow.max_iterations` | 3 | Max iterations per task |
| `workflow.pass_threshold` | 7.0 | Evaluator pass threshold (out of 10) |
| `workflow.auto_merge` | true | Auto-merge branch after pass |
| `workflow.branch_prefix` | "agent" | Task branch prefix |
| `native.gate_full_review_min` | 5 | Escalation score for full human review |
| `native.gate_summary_confirm_min` | 3 | Escalation score for summary confirmation |
| `native.adversarial_model` | "gpt-4.1" | Cross-model reviewer model |
| `native.adversarial_mechanism` | "auto" | Adversarial dispatch mode (`subagent` / `cli` / `auto`) |
| `native.review_gate` | "eng" | Review gate strictness (`eng` = hard gate, `advisory` = log only) |
| `native.plan_review_gate` | "auto" | Plan review gate mode (`human` / `ai` / `auto`) |
| `native.retro_window_days` | 14 | Default retro analysis window in days (1–365) |
| `native.role_models.*` | `{}` | Per-role model overrides: `architect`, `product_owner`, `engineer`, `qa`, `project_manager` |

---

## Command reference

| Command | Description |
|---------|-------------|
| `harness init [--name] [--ci] [-y]` | Initialize project configuration (interactive wizard) |
| `harness install [--force] [--lang]` | Generate native artifacts (.cursor/ skills, agents, rules) |
| `harness status` | Show current progress |
| `harness update [--check] [--force]` | Self-update, reinstall artifacts, check config |
| `harness --version` | Show version |

---

## Task artifacts

All artifacts live under `.agents/` at the project root:

```
.agents/
├── config.toml            # Project config
├── vision.md              # Project vision
├── state.json             # Runtime state
├── tasks/
│   └── task-001/
│       ├── plan.md        # Plan with spec and contract
│       ├── evaluation-r1.md # Review (Markdown)
│       ├── build-r1.log   # Builder log
│       └── ...
└── archive/               # Archived sessions
```

**Local-first**: All state stays on disk; no cloud dependency.

---

## Repository layout

```
harness-orchestrator/
├── src/harness/
│   ├── cli.py              # CLI entry (Typer)
│   ├── commands/            # init, install, update, status
│   ├── core/                # Config, state, UI, events
│   ├── native/              # Cursor-native mode generator
│   ├── templates/           # Jinja2 templates (config + native)
│   └── integrations/        # Git, Memverse
├── tests/                   # Test suite
└── pyproject.toml
```

---

## Internationalization

```bash
harness init --lang zh    # Chinese
harness init --lang en    # English (default)
```

Affects CLI messages and generated files. Stored in `.agents/config.toml` under `[project] lang`.

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
ruff format src/ tests/
```

---

## License

[MIT](LICENSE)
