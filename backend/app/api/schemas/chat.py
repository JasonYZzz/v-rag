"""Chat SSE event schemas."""

from pydantic import BaseModel


class RetrievedChunkOut(BaseModel):
    """Retrieved chunk sent to the frontend citation panel."""

    chunk_id: str
    text: str
    score: float
    page: int | None = None
    document_id: str | None = None
