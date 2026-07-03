"""Tracing helper tests."""

from app.core.observability.tracing import traced


@traced("do_work")
async def do_work() -> str:
    """Return a deterministic value."""

    return "done"


async def test_traced_preserves_return_value() -> None:
    """Decorated functions should preserve return values."""

    assert await do_work() == "done"
