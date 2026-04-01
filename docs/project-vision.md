[中文版](zh-CN/project-vision.md)

# Vision — harness-orchestrator

> **Note (v4.0.0):** Orchestrator mode and CLI drivers are removed; Harness is Cursor-native (skills run in the IDE). Goals below still describe the methodology; “unified abstraction across agent backends” is now IDE-first rather than CLI-driver-based.

## Vision statement

The long-term goal of harness-orchestrator is to be a local-first development orchestration layer for real codebases: it does not replace engineers outright or try to reinvent the IDE, but organizes multiple agent capabilities into an executable, auditable, recoverable engineering loop. For teams and individuals using Cursor, Codex, and similar tools, the value is not “yet another AI entry point,” but converging scattered agent behavior into a single methodology so requirement progress, implementation, and quality gates stay aligned over time.

## Project goals

The core problem is that agent coding is strong locally but still prone to goal drift, broken context, missing quality gates, and opaque processes across continuous work. harness-orchestrator should provide a clear execution framework connecting vision, task selection, design, implementation, evaluation, and reflection, so agents can work steadily toward one project goal instead of restarting from scratch each time.

In the ideal case, users initialize harness in any repo, write a concise vision, and drive multi-role agents forward with unified commands. Every task should leave enough artifacts and state for human review, resuming execution, comparing options, and building trust in autonomous development.

## Key capabilities

1. **Low-friction onboarding** — Embed harness in an existing repo with simple initialization, without restructuring the project for the framework.
2. **Stable multi-role collaboration** — Clear boundaries for Planner, Builder, Evaluator, Strategist, and Reflector, avoiding “one agent does everything” loss of control.
3. **Vision-to-execution loop** — Strategist picks tasks from vision and progress; the workflow advances plan → contract → build → eval and writes results back to the progress system.
4. **Observable, recoverable runs** — Task artifacts, state machine, scores, logs, and archives should support resume after interruption and post-hoc audit.
5. **Unified abstraction across agent backends** — Whether the backend is Cursor or Codex, users experience one methodology, not a pile of ad hoc scripts.
6. **Hard quality constraints** — CI gates, independent review, pass thresholds, and safe stop conditions should be defaults, not optional extras.

## Technical constraints

1. **Local-first** — Prefer local files, branches, and directories for state and artifacts; no heavy server stack required to operate.
2. **Lightweight core** — Stay a Python CLI with controlled dependencies and deployment complexity so individual developers can adopt it directly.
3. **Composable extension** — Drivers, integrations, and methodology should be clearly separated so more agent backends or external systems can be added later.
4. **Structured I/O** — vision, spec, contract, evaluation, and other key documents stay concise, templated, and machine-consumable.
5. **Safety first** — Stronger autonomy must not sacrifice controllability; any automatic advance is bounded by limits, thresholds, and stop conditions.

## Non-goals

1. Not a generic enterprise workflow platform for approvals, releases, data orchestration, and other concerns outside the core scenario.
2. Not chasing a marketing goal of “fully auto-build an entire product”; the focus is sustainable progress on real engineering tasks.
3. Not replacing clear role split with one oversized vague agent; methodology clarity matters more than surface “intelligence.”
4. Not making visualization, SaaS, or cloud hosting the main line of this phase; those only make sense after the core orchestration loop is stable.

## Success criteria

If the project succeeds, users should feel three things clearly:

1. After initializing a new repo, they quickly reach a sustainable multi-agent collaboration mode instead of hand-gluing prompts and scripts.
2. After many development rounds, the project still converges on vision with consistent mechanisms for task choice, implementation quality, and failure recovery.
3. When reviewing the whole process, they can answer plainly: why this task, who did what, why it passed or blocked, and what to do next.
