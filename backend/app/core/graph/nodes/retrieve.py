"""Retrieve graph node."""

from typing import Any

from app.core.graph.state import VragState


async def retrieve(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Retrieve relevant chunks through the injected retrieval service."""

    top_k = int(config.get("top_k", 4))
    hits = await services.retrieval.search(state["query"], top_k=top_k)
    return {
        "retrieved_docs": [
            {
                "chunk_id": hit.chunk_id,
                "text": hit.text,
                "score": hit.score,
                "metadata": hit.metadata,
            }
            for hit in hits
        ]
    }
