[中文版](zh-CN/state-machine.md)

# State Machine

Harness uses an explicit state machine for the task lifecycle. All valid transitions are declared in `src/harness/core/state.py`; any operation that violates transition constraints raises `ValueError`.

## State definitions

| State | Meaning |
|------|------|
| `idle` | No active task |
| `planning` | Planner is producing spec and contract |
| `contracted` | Contract is ready; waiting for Builder |
| `building` | Builder is writing code |
| `evaluating` | Evaluator is reviewing (including CI gate) |
| `done` | Task passed; archived |
| `blocked` | Task blocked (max iterations / driver error / manual stop) |

## Valid transitions

```
idle ──────────► planning
planning ──────► contracted
planning ──────► blocked         (planner failure)
contracted ────► building
building ──────► evaluating
building ──────► blocked         (driver-level error)
evaluating ────► done            (PASS)
evaluating ────► planning        (ITERATE — next round)
evaluating ────► blocked         (max iterations / evaluator failure / stop signal)
done ──────────► idle            (task finished, cleanup)
blocked ───────► idle            (task ended, cleanup)
```

### Flow diagram

```
        ┌──────┐
        │ idle │
        └──┬───┘
           │ start_task()
           ▼
     ┌──────────┐
     │ planning │◄─────────────────────┐
     └────┬─────┘                      │
          │ spec + contract ok         │ ITERATE
          ▼                            │
   ┌────────────┐                      │
   │ contracted │                      │
   └─────┬──────┘                      │
         │                             │
         ▼                             │
    ┌──────────┐                       │
    │ building │                       │
    └────┬─────┘                       │
         │ build done                  │
         ▼                             │
   ┌────────────┐    PASS     ┌──────┐ │
   │ evaluating │────────────►│ done │ │
   └─────┬──────┘             └──────┘ │
         │                             │
         └─────────────────────────────┘
         │
         │ max iter / abort / stop
         ▼
     ┌─────────┐
     │ blocked │
     └─────────┘
```

## Resume behavior

`harness run --resume` restores the last session from `.agents/state.json`:

- If interruption happened at `planning` or later, resume continues from the current `iteration` without resetting the counter
- Artifact filenames use `spec-r{N}.md` / `contract-r{N}.md` / `evaluation-r{N}.md`, where N is the iteration number
- Resume does not overwrite artifacts from prior iterations (iteration number increases)

## Stop signal

- `harness stop` writes the `.agents/.stop` file
- A running task detects the signal after finishing the **current phase** (plan / build / eval) and exits gracefully
- The task transitions to `blocked`
- `Ctrl+C` (SIGINT) saves a checkpoint immediately then exits (exit code 130)

## BLOCKED handling

- `blocked` tasks are not automatically retried
- The `blocked → idle` transition completes automatically in `complete_task()`
- To retry a blocked task, run `harness run "<requirement>"` again (without `--resume`)
