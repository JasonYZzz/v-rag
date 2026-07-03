"""Controlled graph_config schema."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class GraphNodeSpec(BaseModel):
    """A controlled graph node spec."""

    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeSpec(BaseModel):
    """A controlled graph edge spec."""

    model_config = {"populate_by_name": True}

    src: str = Field(alias="from")
    dst: str = Field(alias="to")
    condition: str | None = None


class GraphConfig(BaseModel):
    """Executable routing graph config."""

    version: int = 1
    nodes: list[GraphNodeSpec]
    edges: list[GraphEdgeSpec]
    entry: str
    exits: list[str]

    @model_validator(mode="after")
    def _check_refs(self) -> "GraphConfig":
        ids = {node.id for node in self.nodes}
        if self.entry not in ids:
            raise ValueError(f"entry {self.entry} not in nodes")
        for edge in self.edges:
            if edge.src not in ids or edge.dst not in ids:
                raise ValueError(f"edge references unknown node: {edge.src}->{edge.dst}")
        for exit_id in self.exits:
            if exit_id not in ids:
                raise ValueError(f"exit {exit_id} not in nodes")
        return self
