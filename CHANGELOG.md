# Changelog

## 4.1.50

### Added

- **`harness workflow next`** — prints one machine-readable `HARNESS_NEXT task=… phase=… skill=… hint="…"` line from the latest task’s `workflow-state.json`, using the **same task resolution as `harness gate`** (explicit `--task`, then `HARNESS_TASK_ID`, then latest numeric `task-NNN`).

### Changed

- **Native skill templates (SSOT):** clarify the default pipeline **`/harness-build` → `/harness-ship`**; **`/harness-ship` does not implement feature code** (tests, mandatory 5-role eval, `harness save-eval`, `harness gate`, PR). Added a short **continuity + eval gate** block to plan/build/ship skills to reduce skipped eval and “plan/build then stop” behavior on weaker models. Vision/brainstorm/plan execution text aligned.

## 4.1.0

### Breaking Changes

- **Project renamed** from `harness-orchestrator` to `harness-flow`. Install with `pip install harness-flow`. The Python package name (`harness`) and CLI command (`harness`) are unchanged.
- **Migration:** If upgrading from `harness-orchestrator`, run `pip uninstall harness-orchestrator && pip install harness-flow`.

## 4.0.0 (2026-04-02)

### Breaking Changes

- **Removed orchestrator mode** — The external CLI-driven orchestrator (`harness run`, `harness auto`, `harness stop`, `harness vision`) has been removed. Harness now operates exclusively in cursor-native mode.
- **Removed CLI commands**: `run`, `auto`, `stop`, `vision`
- **Removed modules**: `harness.orchestrator`, `harness.drivers`, `harness.methodology`, `harness.agents` (packaged agent definitions)
- **Removed config fields**: `workflow.mode`, `workflow.profile`, `workflow.dual_evaluation`, `[drivers]` section, `integrations.memverse.driver`
- **Removed role registry**: Orchestrator roles (planner, builder, evaluator, alignment_evaluator, strategist, reflector) removed from `harness.core.roles`

### Migration

- **Old configs are safe**: `HarnessConfig` now uses `extra="ignore"`, so `.agents/config.toml` files with `[drivers]` or removed `[workflow]` fields will load without errors.
- **Use Cursor skills instead of CLI**: `/harness-plan`, `/harness-vision`, `/harness-brainstorm` replace the removed CLI commands.
- **Run `harness install --force`** after upgrading to regenerate native artifacts.

### What's kept

- Full cursor-native mode: skill generation, 5-role review system, Fix-First auto-remediation
- CLI commands: `init`, `install`, `status`, `update`
- Core infrastructure: config, state, UI, events, registry, git ops, scanner
- All native templates and generated artifacts

### Simplified

- `harness init` wizard: 6 steps (was 9) — no IDE probing, no mode selection
- `harness install`: only generates native artifacts (no IDE agent copying)
- `config.py`: cleaner model without driver configs
- `roles.py`: minimal exports (NATIVE_REVIEW_ROLES, SCORING_DIMENSIONS)
- `state.py`: data models only (StateMachine removed)
- i18n catalogs: ~72 keys each (was ~270+)
