"""Built-in graph node registration."""

from pydantic import BaseModel, Field

from app.core.graph.nodes import (
    clarification,
    classifier,
    executor,
    generate,
    memory_recall,
    memory_write,
    planner,
    reflect,
    retrieve,
    synthesizer,
    unsupported,
)
from app.core.graph.registry import NodeDefinition, registry


class RetrieveConfig(BaseModel):
    """Retrieve node config."""

    top_k: int = Field(default=4, ge=1, le=20, description="Number of chunks to retrieve")


class MessageConfig(BaseModel):
    """Terminal message node config."""

    message: str = Field(default="", description="Override response message")


def register_all() -> None:
    """Register all P1 built-in graph nodes idempotently."""

    definitions = [
        NodeDefinition("classifier", "Cascade intent classifier", None, classifier.classify),
        planner.DEFN,
        executor.DEFN,
        synthesizer.DEFN,
        NodeDefinition("retrieve", "Retrieve context chunks", RetrieveConfig, retrieve.retrieve),
        NodeDefinition("generate", "Generate final answer", None, generate.generate),
        NodeDefinition(
            "clarification", "Ask for missing information", MessageConfig, clarification.clarification
        ),
        NodeDefinition("unsupported", "Reject unsupported requests", MessageConfig, unsupported.unsupported),
        NodeDefinition("memory_recall", "P1 memory recall placeholder", None, memory_recall.memory_recall),
        NodeDefinition("memory_write", "P1 memory write placeholder", None, memory_write.memory_write),
        NodeDefinition("reflect", "Judge answer quality and retry branches", None, reflect.reflect),
    ]
    for defn in definitions:
        if not registry.has(defn.type):
            registry.register(defn)
