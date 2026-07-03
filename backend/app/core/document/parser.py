"""Document parsers."""

from typing import Any, cast

import pymupdf

from app.core.document.models import DocumentBlock


def parse_pdf(path: str) -> list[DocumentBlock]:
    """Extract plain text from a PDF, one block per page."""

    blocks: list[DocumentBlock] = []
    pymupdf_api = cast(Any, pymupdf)
    with pymupdf_api.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text().strip()
            if text:
                blocks.append(DocumentBlock(text=text, page=page_number))
    return blocks


def parse_plain_text(text: str) -> list[DocumentBlock]:
    """Parse plain text as a single block."""

    return [DocumentBlock(text=text, page=1)]
