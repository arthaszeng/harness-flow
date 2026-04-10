"""Memverse integration — payload builders for MCP-mediated dual-write.

Memverse is accessed exclusively via Cursor MCP tools.  Python code does NOT
call Memverse directly.  Instead, this module provides pure data-formatting
functions that produce the exact arguments needed for MCP tool calls
(``upsert_memory``, ``search_memory``).

The generated skill/agent templates embed these payloads as MCP call
instructions so the Cursor agent executes them within its authenticated
MCP session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


FAILURE_PATTERN_DOMAIN = "harness-flow"
FAILURE_PATTERN_TYPE = "failure-pattern"
FAILURE_PATTERN_UPSERT_KEY = "signature"


@dataclass(frozen=True)
class MemverseUpsertPayload:
    """Pre-formatted arguments for MCP ``upsert_memory`` tool call."""

    tool: str = "upsert_memory"
    content: str = ""
    metadata: str = ""
    upsert_key: str = FAILURE_PATTERN_UPSERT_KEY
    domain: str = FAILURE_PATTERN_DOMAIN

    def as_dict(self) -> dict[str, str]:
        return {
            "content": self.content,
            "metadata": self.metadata,
            "upsert_key": self.upsert_key,
            "domain": self.domain,
        }


@dataclass(frozen=True)
class MemverseSearchPayload:
    """Pre-formatted arguments for MCP ``search_memory`` tool call."""

    tool: str = "search_memory"
    query: str = ""
    domains: str = FAILURE_PATTERN_DOMAIN
    metadata_filter: str = ""
    limit: int = 20

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "domains": self.domains,
            "metadata_filter": self.metadata_filter,
            "limit": self.limit,
        }


@dataclass
class FailurePatternSync:
    """Result of preparing a failure pattern for Memverse sync.

    Produced by ``build_upsert_payload`` and attached to the
    ``FailurePattern`` return value so callers (CLI, templates) can
    decide whether/when to execute the MCP call.
    """

    payload: MemverseUpsertPayload
    skipped: bool = False
    skip_reason: str = ""


def build_upsert_payload(
    *,
    summary: str,
    category: str,
    phase: str,
    task_id: str,
    fp_id: str,
    signature: str,
    first_seen: str,
    error_output: str = "",
    root_cause: str = "",
    fix_applied: str = "",
    domain: str = FAILURE_PATTERN_DOMAIN,
) -> FailurePatternSync:
    """Build a ``MemverseUpsertPayload`` from failure pattern fields.

    The content is human-readable; metadata carries structured fields for
    ``metadata_filter`` queries.  The normalized *signature* is the dedup
    key so identical failures across tasks converge to one Memverse memory.
    """
    content_parts = [f"[failure-pattern] {summary}"]
    content_parts.append(f"Category: {category} | Phase: {phase} | Task: {task_id}")
    if root_cause:
        content_parts.append(f"Root cause: {root_cause}")
    if fix_applied:
        content_parts.append(f"Fix: {fix_applied}")
    if error_output:
        content_parts.append(f"Error: {error_output[:500]}")

    meta = {
        "type": FAILURE_PATTERN_TYPE,
        "category": category,
        "phase": phase,
        "task_id": task_id,
        "fp_id": fp_id,
        "first_seen": first_seen,
        FAILURE_PATTERN_UPSERT_KEY: signature,
    }

    return FailurePatternSync(
        payload=MemverseUpsertPayload(
            content="\n".join(content_parts),
            metadata=json.dumps(meta),
            domain=domain,
        ),
    )


def build_search_payload(
    *,
    query: str,
    category: str = "",
    domain: str = FAILURE_PATTERN_DOMAIN,
    limit: int = 20,
) -> MemverseSearchPayload:
    """Build a ``MemverseSearchPayload`` for failure pattern search."""
    meta_filter: dict[str, str] = {"type": FAILURE_PATTERN_TYPE}
    if category:
        meta_filter["category"] = category

    return MemverseSearchPayload(
        query=query or "failure pattern",
        domains=domain,
        metadata_filter=json.dumps(meta_filter),
        limit=limit,
    )
