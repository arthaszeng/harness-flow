> **Note (v4.0.0):** This benchmark was designed for orchestrator mode (`harness run`), which has been removed. The benchmark scripts will not work with v4.0.0+. For cursor-native workflows, use `/harness-plan` in Cursor IDE instead.

# Benchmark: TODO API

Compare Harness orchestration with using Codex or Cursor directly.

## Test project

A minimal Python TODO API (FastAPI + SQLite), starting from an empty project.

## Five incremental tasks

| # | Task | Expected complexity |
|---|------|-----------|
| 1 | Bootstrap FastAPI project, health check endpoint, basic project layout | simple |
| 2 | Implement TODO CRUD API (create, read, update, delete) + SQLite storage | medium |
| 3 | Add input validation, error handling, and Pydantic models | medium |
| 4 | Implement pagination, filtering (by status), and sorting | medium |
| 5 | Add a full pytest suite covering all endpoints and edge cases | complex |

## Three modes

### A. Codex only
```bash
codex exec --full-auto - <<< "task description"
```

### B. Cursor only
```bash
cursor agent --print --force "task description"
```

### C. Harness orchestration
```bash
harness init --name todo-api --ci "pytest" -y
harness run "task description"
```

## Comparison metrics

| Metric | Description |
|------|------|
| **Completion rate** | Share of the 5 tasks completed successfully |
| **Average iterations** | Rounds per task from start to pass |
| **CI first-pass rate** | Share where CI passes after the first build round |
| **Manual interventions** | Times human code edits were needed to proceed |
| **Replayability** | Whether decisions can be fully traced afterward |

## How to run

### Setup
```bash
mkdir /tmp/todo-benchmark && cd /tmp/todo-benchmark
git init && git commit --allow-empty -m "init"
```

### Mode C: Harness (recommended first — produces full artifacts)
```bash
pip install harness-orchestrator
harness install
harness init --name todo-api --ci "pytest" -y

# Run tasks one by one
harness run "Bootstrap FastAPI project, health check endpoint, basic project layout"
harness run "Implement TODO CRUD API (create, read, update, delete) + SQLite storage"
harness run "Add input validation, error handling, and Pydantic models"
harness run "Implement pagination, filtering by status, and sorting"
harness run "Add a full pytest suite covering all endpoints and edge cases"
```

### Demo highlights

- **Resume after Ctrl+C mid-task**: During task 3, press Ctrl+C, then `harness run "..." --resume`
- **Inspect artifacts**: `ls .agents/tasks/` for per-round spec, contract, evaluation
- **Inspect events**: `cat .agents/runs/*/events.jsonl | python -m json.tool`
- **JSON sidecar**: `cat .agents/tasks/task-001/contract-r1.json`

## Results template

```markdown
| Metric | Codex | Cursor | Harness |
|--------|-------|--------|---------|
| Completion rate | ?/5 | ?/5 | ?/5 |
| Avg. iterations | N/A | N/A | ? |
| CI first-pass rate | ?% | ?% | ?% |
| Manual interventions | ? | ? | ? |
| Replayability | None | None | Full |
```
