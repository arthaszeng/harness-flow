"""Memverse integration — disabled by default, failure non-blocking, clear fallback.

Design:
  Actual Memverse search/add runs indirectly via the reflector agent's MCP tools;
  Python does not call MCP directly. Therefore:
  - NullMemverse always returns empty results safely
  - SafeMemverse wraps any implementation so failures do not block the main flow
  - If Python should call MCP directly later, implement it inside SafeMemverse with isolated exceptions
"""

from __future__ import annotations

import sys
from typing import Protocol, runtime_checkable


@runtime_checkable
class MemverseClient(Protocol):
    def search(self, query: str, domain: str) -> list[str]: ...
    def add(self, text: str, domain: str) -> None: ...
    @property
    def enabled(self) -> bool: ...


class NullMemverse:
    """No-op implementation when Memverse is disabled."""

    @property
    def enabled(self) -> bool:
        return False

    def search(self, query: str, domain: str) -> list[str]:
        return []

    def add(self, text: str, domain: str) -> None:
        pass


class SafeMemverse:
    """Wraps a MemverseClient to ensure all calls are non-blocking on failure.

    Any exception from the inner client is caught, logged to stderr, and
    silently swallowed so that the main workflow is never interrupted.
    """

    def __init__(self, inner: MemverseClient) -> None:
        self._inner = inner

    @property
    def enabled(self) -> bool:
        return self._inner.enabled

    def search(self, query: str, domain: str) -> list[str]:
        try:
            return self._inner.search(query, domain)
        except Exception as exc:
            sys.stderr.write(f"[harness] memverse search failed (non-blocking): {exc}\n")
            return []

    def add(self, text: str, domain: str) -> None:
        try:
            self._inner.add(text, domain)
        except Exception as exc:
            sys.stderr.write(f"[harness] memverse add failed (non-blocking): {exc}\n")


class _PromptMemverse:
    """Memverse enabled but delegated to agent prompts.

    The reflector agent's prompt includes MCP memverse instructions.
    This class marks memverse as "enabled" so the reflector prompt
    includes the memverse write/search directives, but Python-side
    search/add are no-ops (the agent handles it via MCP tools).
    """

    @property
    def enabled(self) -> bool:
        return True

    def search(self, query: str, domain: str) -> list[str]:
        return []

    def add(self, text: str, domain: str) -> None:
        pass


def create_memverse(
    enabled: bool,
    driver: object | None = None,
) -> MemverseClient:
    """Create a Memverse client.

    - disabled → NullMemverse (zero overhead)
    - enabled  → SafeMemverse(_PromptMemverse()) (non-blocking, prompt-based)
    """
    if not enabled:
        return NullMemverse()
    return SafeMemverse(_PromptMemverse())
