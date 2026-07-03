"""Document upload and indexing endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.db.models import Chunk, Document
from app.core.db.session import get_session_factory
from app.core.document.chunker import chunk_blocks
from app.core.document.parser import parse_plain_text
from app.core.provider.base import EmbeddingProvider
from app.core.retrieval.engine import RetrievalEngine
from app.deps import get_embedder, get_retrieval

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    retrieval: Annotated[RetrievalEngine, Depends(get_retrieval)],
    embedder: Annotated[EmbeddingProvider, Depends(get_embedder)],
) -> dict[str, str]:
    """Upload a text document, parse, chunk, embed, and index it."""

    content = (await file.read()).decode("utf-8", errors="ignore")
    blocks = parse_plain_text(content)
    chunks = chunk_blocks(blocks)
    texts = [chunk.text for chunk in chunks]
    vectors = await embedder.embed(texts) if texts else []

    document_id = str(uuid.uuid4())
    session_factory = get_session_factory()
    index_payload: list[tuple[str, list[float], dict[str, object]]] = []

    async with session_factory() as session:
        document = Document(
            id=document_id,
            filename=file.filename or "upload",
            source_path=f"/uploads/{document_id}",
        )
        session.add(document)
        for vector, block in zip(vectors, chunks, strict=True):
            chunk = Chunk(text=block.text, page=block.page, document=document)
            session.add(chunk)
            await session.flush()
            index_payload.append(
                (
                    chunk.id,
                    vector,
                    {"doc": document_id, "page": block.page, "text": block.text},
                )
            )
        await session.commit()

    await retrieval.index(index_payload)
    return {"document_id": document_id, "chunks": str(len(chunks))}
