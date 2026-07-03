"""Document parser and chunker tests."""

from app.core.document.chunker import chunk_blocks, split_text
from app.core.document.models import DocumentBlock
from app.core.document.parser import parse_plain_text


def test_split_text_respects_size_and_overlap() -> None:
    """Chunks should respect size and overlap."""

    chunks = split_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_split_text_short_text_single_chunk() -> None:
    """Short text should return one chunk."""

    assert split_text("hi", chunk_size=100) == ["hi"]


def test_chunk_blocks_preserves_page() -> None:
    """Child chunks should inherit the source page."""

    blocks = [DocumentBlock(text="x" * 600, page=3)]
    chunks = chunk_blocks(blocks, chunk_size=500, overlap=50)

    assert len(chunks) == 2
    assert all(chunk.page == 3 for chunk in chunks)


def test_parse_plain_text() -> None:
    """Plain text should parse into one block."""

    assert parse_plain_text("hello") == [DocumentBlock(text="hello", page=1)]
