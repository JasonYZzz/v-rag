"""Document upload and indexing endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from app.core.db.models import Chunk, Document
from app.core.db.session import get_session_factory
from app.core.document.chunker import chunk_blocks
from app.core.document.parser import parse_plain_text
from app.core.provider.base import EmbeddingProvider
from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.base import VectorStore
from app.deps import get_embedder, get_retrieval, get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    """Document list item."""

    id: str
    filename: str
    chunks: int
    created_at: str


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


@router.get("")
async def list_documents() -> list[DocumentOut]:
    """List documents and their chunk counts."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        chunk_counts = (
            select(Chunk.document_id, func.count(Chunk.id).label("chunk_count"))
            .group_by(Chunk.document_id)
            .subquery()
        )
        stmt: Select[tuple[Document, int]] = (
            select(Document, func.coalesce(chunk_counts.c.chunk_count, 0))
            .outerjoin(chunk_counts, Document.id == chunk_counts.c.document_id)
            .order_by(Document.created_at.desc())
        )
        rows = (await session.execute(stmt)).all()
        return [
            DocumentOut(
                id=document.id,
                filename=document.filename,
                chunks=int(chunk_count),
                created_at=document.created_at.isoformat() if document.created_at else "",
            )
            for document, chunk_count in rows
        ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    store: Annotated[VectorStore, Depends(get_vector_store)],
) -> dict[str, str]:
    """Delete a document, its chunks, and matching vector index entries."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        document = await session.get(
            Document,
            document_id,
            options=(selectinload(Document.chunks),),
        )
        if document is None:
            raise HTTPException(status_code=404, detail="document not found")
        chunk_ids = [chunk.id for chunk in document.chunks]
        await session.delete(document)
        await session.commit()

    if chunk_ids:
        await store.delete(chunk_ids)
    return {"deleted": document_id}
