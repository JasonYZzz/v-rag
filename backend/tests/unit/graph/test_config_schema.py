"""Controlled graph_config schema tests."""

import pytest
from pydantic import ValidationError

from app.core.graph.config import GraphConfig


def test_valid_graph_config_passes() -> None:
    """A graph with known node references should validate."""

    config = GraphConfig.model_validate(
        {
            "version": 1,
            "entry": "classifier",
            "nodes": [
                {"id": "classifier", "type": "classifier"},
                {"id": "generate", "type": "generate", "config": {"temperature": 0}},
            ],
            "edges": [{"from": "classifier", "to": "generate"}],
            "exits": ["generate"],
        }
    )

    assert config.edges[0].src == "classifier"
    assert config.edges[0].dst == "generate"
    assert config.nodes[1].config == {"temperature": 0}


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"entry": "missing"}, "entry missing not in nodes"),
        ({"edges": [{"from": "classifier", "to": "missing"}]}, "edge references unknown node"),
        ({"exits": ["missing"]}, "exit missing not in nodes"),
    ],
)
def test_invalid_references_raise_validation_error(
    patch: dict[str, object], message: str
) -> None:
    """Entry, edge, and exit references must stay inside declared nodes."""

    raw: dict[str, object] = {
        "version": 1,
        "entry": "classifier",
        "nodes": [
            {"id": "classifier", "type": "classifier"},
            {"id": "generate", "type": "generate"},
        ],
        "edges": [{"from": "classifier", "to": "generate"}],
        "exits": ["generate"],
    }
    raw.update(patch)

    with pytest.raises(ValidationError, match=message):
        GraphConfig.model_validate(raw)
