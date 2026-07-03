"""Node registry whitelist tests."""

from typing import Any

import pytest
from pydantic import BaseModel

from app.core.graph.registry import NodeDefinition, NodeRegistry
from app.core.graph.state import VragState


class FakeConfig(BaseModel):
    """Fake node config."""


def fake_execute(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Return a tiny node patch."""

    _ = (state, config, services)
    return {"generation": "ok"}


def test_register_get_has_and_list() -> None:
    """Registered node types should be discoverable by whitelist APIs."""

    registry = NodeRegistry()
    defn = NodeDefinition(
        type="fake",
        description="Fake node",
        config_schema=FakeConfig,
        execute=fake_execute,
    )

    registry.register(defn)

    assert registry.has("fake")
    assert registry.get("fake") == defn
    assert registry.list() == ["fake"]


def test_duplicate_type_raises() -> None:
    """Node types should be unique."""

    registry = NodeRegistry()
    defn = NodeDefinition(
        type="fake",
        description="Fake node",
        config_schema=None,
        execute=fake_execute,
    )

    registry.register(defn)

    with pytest.raises(ValueError, match="node type already registered"):
        registry.register(defn)


def test_get_unknown_type_raises_key_error() -> None:
    """Unknown node types should not be silently accepted."""

    registry = NodeRegistry()

    with pytest.raises(KeyError, match="unknown node type"):
        registry.get("missing")
