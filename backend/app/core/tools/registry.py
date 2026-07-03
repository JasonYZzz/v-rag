"""Self-hosted Tool Registry for whitelisted executor tools."""

from dataclasses import dataclass
from typing import Any, Protocol


class ToolFunc(Protocol):
    """Tool execution protocol."""

    async def __call__(self, args: dict[str, Any], services: Any) -> dict[str, Any]:
        """Execute a tool with structured arguments."""


@dataclass(frozen=True)
class ToolDefinition:
    """Whitelisted tool definition."""

    name: str
    description: str
    input_schema: type | None
    execute: ToolFunc


class ToolRegistry:
    """Fail-closed registry for self-hosted tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, defn: ToolDefinition) -> None:
        """Register a tool definition."""

        if defn.name in self._tools:
            raise ValueError(f"tool already registered: {defn.name}")
        self._tools[defn.name] = defn

    def get(self, name: str) -> ToolDefinition:
        """Return a tool definition or raise."""

        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def list(self) -> list[str]:
        """Return registered tool names in stable order."""

        return sorted(self._tools)


tool_registry = ToolRegistry()

