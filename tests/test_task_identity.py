"""Tests for task identity resolution."""

from __future__ import annotations

import pytest

from harness.core.task_identity import TaskIdentityResolver


def test_hybrid_strategy_accepts_numeric_and_jira():
    resolver = TaskIdentityResolver(strategy="hybrid")
    assert resolver.is_valid_task_key("task-001")
    assert resolver.is_valid_task_key("PROJ-123")
    assert not resolver.is_valid_task_key("feature-foo")


def test_custom_strategy_validates_pattern():
    resolver = TaskIdentityResolver(strategy="custom", custom_pattern=r"[a-z]{3}-\d+")
    assert resolver.is_valid_task_key("abc-42")
    assert not resolver.is_valid_task_key("ABC-42")


def test_custom_strategy_rejects_unsafe_pattern():
    with pytest.raises(ValueError):
        TaskIdentityResolver(strategy="custom", custom_pattern=r"(?=abc)abc").fullmatch_re


@pytest.mark.parametrize(
    "branch,expected",
    [
        ("agent/task-010-feature", "task-010"),
        ("agent/PROJ-1234-git-governance", "PROJ-1234"),
        ("main", None),
        ("feature/task-010", None),
    ],
)
def test_extract_from_branch_hybrid(branch: str, expected: str | None):
    resolver = TaskIdentityResolver(strategy="hybrid")
    assert resolver.extract_from_branch(branch) == expected

