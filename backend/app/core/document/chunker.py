"""Document chunking helpers."""

from app.core.document.models import DocumentBlock


def split_text(text: str, *, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into fixed-size chunks with overlap."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def chunk_blocks(
    blocks: list[DocumentBlock],
    *,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[DocumentBlock]:
    """Split blocks and preserve page and heading metadata."""

    chunks: list[DocumentBlock] = []
    for block in blocks:
        for piece in split_text(block.text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                DocumentBlock(
                    text=piece,
                    page=block.page,
                    block_type=block.block_type,
                    heading_path=block.heading_path,
                )
            )
    return chunks
