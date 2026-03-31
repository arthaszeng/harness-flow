"""Translate raw agent/CI output into actionable hints for the next iteration.

Inspired by gstack's wrapError() pattern — error messages target AI agents,
not human developers. Each hint tells the agent *what to do next*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    CI_SYNTAX = "ci_syntax"
    CI_TEST_FAILURE = "ci_test_failure"
    CI_LINT = "ci_lint"
    CI_TYPE_CHECK = "ci_type_check"
    CI_TIMEOUT = "ci_timeout"
    CI_MISSING_COMMAND = "ci_missing_command"
    BUILD_TIMEOUT = "build_timeout"
    BUILD_NO_CHANGES = "build_no_changes"
    DRIVER_ERROR = "driver_error"
    IMPORT_ERROR = "import_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorHint:
    category: ErrorCategory
    summary: str
    key_lines: list[str]
    suggestion: str


_PATTERNS: list[tuple[re.Pattern[str], ErrorCategory, str]] = [
    # Python-specific
    (
        re.compile(r"SyntaxError:", re.IGNORECASE),
        ErrorCategory.CI_SYNTAX,
        "Fix the syntax error in the indicated file and line, then re-run CI.",
    ),
    (
        re.compile(r"IndentationError:", re.IGNORECASE),
        ErrorCategory.CI_SYNTAX,
        "Fix the indentation error at the indicated location.",
    ),
    (
        re.compile(r"ImportError:|ModuleNotFoundError:", re.IGNORECASE),
        ErrorCategory.IMPORT_ERROR,
        "A required module is missing or misspelled. Check the import path and ensure the dependency is installed.",
    ),
    (
        re.compile(r"(?:FAILED|ERRORS?)\s+.*test", re.IGNORECASE),
        ErrorCategory.CI_TEST_FAILURE,
        "One or more tests failed. Read the failure messages below, fix the code or tests, and re-run.",
    ),
    (
        re.compile(r"AssertionError:|assert\s+", re.IGNORECASE),
        ErrorCategory.CI_TEST_FAILURE,
        "An assertion failed in a test. Check the expected vs actual values and fix the implementation.",
    ),
    # Lint / type-check
    (
        re.compile(r"(?:ruff|flake8|pylint|eslint|mypy|pyright)\s", re.IGNORECASE),
        ErrorCategory.CI_LINT,
        "Linter or type checker reported issues. Fix the flagged lines to pass CI.",
    ),
    (
        re.compile(r"error: .* incompatible type", re.IGNORECASE),
        ErrorCategory.CI_TYPE_CHECK,
        "Type checking failed. Fix the type annotations or value assignments indicated.",
    ),
    # Timeout
    (
        re.compile(r"timed?\s*out|timeout", re.IGNORECASE),
        ErrorCategory.CI_TIMEOUT,
        "The CI command timed out. Check for infinite loops, missing test fixtures, or slow operations.",
    ),
    # Missing command
    (
        re.compile(r"command not found|No such file or directory.*(?:make|npm|pytest)", re.IGNORECASE),
        ErrorCategory.CI_MISSING_COMMAND,
        "The CI command binary was not found. Verify the command exists and PATH is correct.",
    ),
]

_KEY_LINE_PATTERNS = [
    re.compile(r"(?:File|Error|FAILED|FAIL|assert|raise)\s", re.IGNORECASE),
    re.compile(r"^\s*(?:E\s|>|×|✗|FAILED|ERROR)", re.MULTILINE),
    re.compile(r"line \d+", re.IGNORECASE),
]

_MAX_KEY_LINES = 15


def _extract_key_lines(output: str) -> list[str]:
    """Pull the most informative lines from raw output."""
    lines = output.split("\n")
    key: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pat in _KEY_LINE_PATTERNS:
            if pat.search(stripped):
                key.append(stripped)
                break
    if len(key) > _MAX_KEY_LINES:
        key = key[:_MAX_KEY_LINES]
    return key


def classify_error(output: str) -> ErrorCategory:
    """Determine the error category from raw output text."""
    for pattern, category, _ in _PATTERNS:
        if pattern.search(output):
            return category
    return ErrorCategory.UNKNOWN


def translate_error(output: str, *, elapsed: float = 0.0) -> ErrorHint:
    """Classify raw error output and produce an actionable hint for the agent.

    Args:
        output: Raw stdout/stderr from CI or builder.
        elapsed: Wall-clock seconds the command ran.

    Returns:
        ErrorHint with category, summary, key lines, and a next-step suggestion.
    """
    category = classify_error(output)

    for pattern, cat, suggestion in _PATTERNS:
        if cat == category and pattern.search(output):
            match = pattern.search(output)
            summary = match.group(0).strip() if match else category.value
            break
    else:
        summary = "Unknown error"
        suggestion = "Review the full output below and address the root cause."

    key_lines = _extract_key_lines(output)

    return ErrorHint(
        category=category,
        summary=summary,
        key_lines=key_lines,
        suggestion=suggestion,
    )


def format_error_feedback(
    hint: ErrorHint,
    raw_output: str,
    *,
    max_raw_chars: int = 2000,
) -> str:
    """Format an ErrorHint into a structured feedback string for the next agent iteration.

    Returns Markdown that the planner/builder can parse:
    - Error category and summary for quick triage
    - Key error lines extracted from the output
    - Actionable suggestion for the next step
    - Truncated raw output as fallback context
    """
    parts: list[str] = []
    parts.append(f"## Error Analysis\n**Category**: {hint.category.value}\n**Summary**: {hint.summary}")
    parts.append(f"\n**Suggested fix**: {hint.suggestion}")

    if hint.key_lines:
        lines_block = "\n".join(hint.key_lines)
        parts.append(f"\n### Key error lines\n```\n{lines_block}\n```")

    tail = raw_output[-max_raw_chars:] if len(raw_output) > max_raw_chars else raw_output
    parts.append(f"\n### Raw output (tail)\n```\n{tail}\n```")

    return "\n".join(parts)
