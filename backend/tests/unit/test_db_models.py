"""Metadata model tests using in-memory sqlite."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.db.models import Base, Chunk, Document


async def test_document_chunk_relationship() -> None:
    """Document and Chunk should save and query through their relationship."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        doc = Document(filename="a.pdf", source_path="/tmp/a.pdf")
        doc.chunks.append(Chunk(text="hello", page=1))
        session.add(doc)
        await session.commit()

        result = await session.execute(
            select(Document).options(selectinload(Document.chunks)).where(Document.id == doc.id)
        )
        loaded = result.scalar_one()

        assert loaded.filename == "a.pdf"
        assert len(loaded.chunks) == 1
        assert loaded.chunks[0].text == "hello"
