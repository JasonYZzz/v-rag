"""Built-in graph node registration."""

from app.core.graph.nodes import (
    clarification,
    classifier,
    generate,
    memory_recall,
    memory_write,
    reflect,
    retrieve,
    unsupported,
)
from app.core.graph.registry import NodeDefinition, registry


def register_all() -> None:
    """Register all P1 built-in graph nodes idempotently."""

    definitions = [
        NodeDefinition("classifier", "Cascade intent classifier", None, classifier.classify),
        NodeDefinition("retrieve", "Retrieve context chunks", None, retrieve.retrieve),
        NodeDefinition("generate", "Generate final answer", None, generate.generate),
        NodeDefinition("clarification", "Ask for missing information", None, clarification.clarification),
        NodeDefinition("unsupported", "Reject unsupported requests", None, unsupported.unsupported),
        NodeDefinition("memory_recall", "P1 memory recall placeholder", None, memory_recall.memory_recall),
        NodeDefinition("memory_write", "P1 memory write placeholder", None, memory_write.memory_write),
        NodeDefinition("reflect", "P1 reflection placeholder", None, reflect.reflect),
    ]
    for defn in definitions:
        if not registry.has(defn.type):
            registry.register(defn)
