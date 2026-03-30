"""Memverse 集成 — 完全可选（NullObject 模式），支持任意 IDE driver"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemverseClient(Protocol):
    def search(self, query: str, domain: str) -> list[str]: ...
    def add(self, text: str, domain: str) -> None: ...


class NullMemverse:
    """Memverse 关闭时的空实现"""

    def search(self, query: str, domain: str) -> list[str]:
        return []

    def add(self, text: str, domain: str) -> None:
        pass


class LiveMemverse:
    """通过 IDE CLI MCP 调用 Memverse（Cursor / Codex 均可）"""

    def __init__(self, driver: object) -> None:
        self._driver = driver

    def search(self, query: str, domain: str) -> list[str]:
        # 通过 agent 间接调用 MCP search_memory
        # 简化实现：返回空列表，实际使用时通过 agent prompt 读取
        return []

    def add(self, text: str, domain: str) -> None:
        # 通过 agent 间接调用 MCP add_memories
        # 简化实现：在 reflector agent 的 prompt 中嵌入 memverse 写入指令
        pass


def create_memverse(
    enabled: bool,
    driver: object | None = None,
) -> MemverseClient:
    """创建 Memverse 客户端，driver 可以是任意 AgentDriver（Codex / Cursor）"""
    if enabled and driver is not None:
        return LiveMemverse(driver)
    return NullMemverse()
