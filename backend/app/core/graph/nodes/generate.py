"""Generate graph node."""

from typing import Any

from app.core.graph.state import VragState


async def generate(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Generate an answer from retrieved context."""

    _ = config
    docs = state.get("retrieved_docs", [])
    context = "\n---\n".join(str(doc.get("text", "")) for doc in docs)
    memory_context = "\n".join(str(block) for block in state.get("context_blocks", []) if block)
    prompt = f"Memory:\n{memory_context}\n\nContext:\n{context}\n\nQuestion: {state['query']}"
    text = await services.llm.complete(prompt, system="You are the v-rag assistant.")
    return {"generation": text}
