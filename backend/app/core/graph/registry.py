"""Node Registry: backend whitelists executable node types."""

import builtins
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.graph.state import VragState


class NodeFunc(Protocol):
    """Node execution function."""

    def __call__(
        self, state: VragState, config: dict[str, Any], services: Any
    ) -> dict[str, Any]: ...


class AsyncNodeFunc(Protocol):
    """Async node execution function."""

    async def __call__(
        self, state: VragState, config: dict[str, Any], services: Any
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class NodeDefinition:
    """Whitelisted node type definition."""

    type: str
    description: str
    config_schema: builtins.type[BaseModel] | None
    execute: NodeFunc | AsyncNodeFunc


class NodeRegistry:
    """Global node whitelist registry."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeDefinition] = {}

    def register(self, defn: NodeDefinition) -> None:
        """Register a node type."""

        if defn.type in self._nodes:
            raise ValueError(f"node type already registered: {defn.type}")
        self._nodes[defn.type] = defn

    def has(self, type_: str) -> bool:
        """Return whether a node type is registered."""

        return type_ in self._nodes

    def get(self, type_: str) -> NodeDefinition:
        """Return a registered node type or raise."""

        if type_ not in self._nodes:
            raise KeyError(f"unknown node type: {type_}")
        return self._nodes[type_]

    def list(self) -> list[str]:
        """Return registered node types in stable order."""

        return sorted(self._nodes)

    def clear(self) -> None:
        """Clear all node types. Intended for tests."""

        self._nodes.clear()


registry = NodeRegistry()
