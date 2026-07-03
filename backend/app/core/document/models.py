"""Canonical document block models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentBlock:
    """Normalized parser output block."""

    text: str
    page: int | None = None
    block_type: str = "paragraph"
    heading_path: tuple[str, ...] = ()
