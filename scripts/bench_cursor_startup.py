#!/usr/bin/env python3
"""A/B benchmark: cursor-agent (direct) vs cursor agent (shim).

Measures:
  1. --help startup latency (multiple runs, averaged)
  2. First-token latency with a trivial prompt (stdin vs CLI arg)

Usage:
    python scripts/bench_cursor_startup.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time

RUNS = 5
PROMPT = "Say hello in one word"
TIMEOUT = 60


def _time_help(cmd: list[str], label: str) -> list[float]:
    """Run ``cmd`` RUNS times and return elapsed times."""
    times: list[float] = []
    for i in range(RUNS):
        t0 = time.monotonic()
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            times.append(10.0)
            continue
        elapsed = time.monotonic() - t0
        times.append(elapsed)
        sys.stdout.write(f"  {label} #{i+1}: {elapsed:.3f}s\n")
        sys.stdout.flush()
    return times


def _time_first_token_stdin(cmd: list[str], prompt: str, label: str) -> float | None:
    """Spawn ``cmd`` with prompt on stdin, return time-to-first-stdout-line."""
    t0 = time.monotonic()
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    try:
        assert proc.stdin is not None
        proc.stdin.write(prompt)
        proc.stdin.close()

        assert proc.stdout is not None
        first_line = proc.stdout.readline()
        if first_line:
            elapsed = time.monotonic() - t0
            sys.stdout.write(f"  {label}: first line in {elapsed:.3f}s\n")
            sys.stdout.flush()
            proc.kill()
            proc.wait(timeout=5)
            return elapsed
    except Exception as e:
        sys.stdout.write(f"  {label}: error — {e}\n")
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        proc.wait(timeout=5)
    return None


def _time_first_token_arg(cmd: list[str], label: str) -> float | None:
    """Spawn ``cmd`` (prompt already in argv), return time-to-first-stdout-line."""
    t0 = time.monotonic()
    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    try:
        assert proc.stdout is not None
        first_line = proc.stdout.readline()
        if first_line:
            elapsed = time.monotonic() - t0
            sys.stdout.write(f"  {label}: first line in {elapsed:.3f}s\n")
            sys.stdout.flush()
            proc.kill()
            proc.wait(timeout=5)
            return elapsed
    except Exception as e:
        sys.stdout.write(f"  {label}: error — {e}\n")
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        proc.wait(timeout=5)
    return None


def _avg(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def main() -> None:
    has_cursor_agent = shutil.which("cursor-agent") is not None
    has_cursor = shutil.which("cursor") is not None

    if not has_cursor_agent and not has_cursor:
        sys.stderr.write("Neither cursor-agent nor cursor found in PATH\n")
        sys.exit(1)

    print("=" * 60)
    print("Cursor Driver Startup Benchmark")
    print("=" * 60)

    # ── Test 1: --help latency ──────────────────────────────────
    results: dict[str, dict] = {}

    if has_cursor_agent:
        print(f"\n--- Test 1a: cursor-agent --help ({RUNS} runs) ---")
        t1a = _time_help(["cursor-agent", "--help"], "cursor-agent")
        results["cursor-agent --help"] = {"avg": _avg(t1a), "times": t1a}

    if has_cursor:
        print(f"\n--- Test 1b: cursor agent --help ({RUNS} runs) ---")
        t1b = _time_help(["cursor", "agent", "--help"], "cursor agent")
        results["cursor agent --help"] = {"avg": _avg(t1b), "times": t1b}

    # ── Test 2: First-token latency ─────────────────────────────
    if has_cursor_agent:
        print("\n--- Test 2a: cursor-agent first token (stdin, new flags) ---")
        new_cmd = [
            "cursor-agent", "-p", "--force",
            "--output-format", "stream-json",
            "--stream-partial-output",
        ]
        t2a = _time_first_token_stdin(new_cmd, PROMPT, "new (stdin)")
        if t2a is not None:
            results["new: first token (stdin)"] = {"avg": t2a}

    if has_cursor_agent:
        print("\n--- Test 2b: cursor-agent first token (CLI arg, old flags) ---")
        old_cmd = [
            "cursor-agent", "--print", "--trust",
            "--approve-mcps",
            "--output-format", "stream-json",
            "--stream-partial-output",
            "--force",
            PROMPT,
        ]
        t2b = _time_first_token_arg(old_cmd, "old (arg)")
        if t2b is not None:
            results["old: first token (CLI arg)"] = {"avg": t2b}

    # ── Summary table ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\n| {'Test':<35} | {'Avg (s)':>8} |")
    print(f"|{'-'*37}|{'-'*10}|")
    for name, data in results.items():
        print(f"| {name:<35} | {data['avg']:>7.3f}s |")

    if "cursor-agent --help" in results and "cursor agent --help" in results:
        a = results["cursor-agent --help"]["avg"]
        b = results["cursor agent --help"]["avg"]
        speedup = b / a if a > 0 else 0
        print(f"\n  --help speedup: {speedup:.1f}x faster with cursor-agent")

    print()


if __name__ == "__main__":
    main()
