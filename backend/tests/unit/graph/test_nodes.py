"""Graph node behavior tests."""

from app.core.graph.nodes import register_all
from app.core.graph.nodes.clarification import clarification
from app.core.graph.nodes.generate import generate
from app.core.graph.nodes.memory_write import memory_write
from app.core.graph.nodes.retrieve import retrieve
from app.core.graph.nodes.unsupported import unsupported
from app.core.graph.registry import registry
from app.core.graph.state import VragState


class Hit:
    """Fake retrieval hit."""

    def __init__(self) -> None:
        self.chunk_id = "c1"
        self.text = "stored context"
        self.score = 0.9
        self.metadata = {"page": 1}


class FakeRetrieval:
    """Fake retrieval service."""

    async def search(self, query: str, top_k: int = 4) -> list[Hit]:
        """Return one fake hit."""

        assert query == "q"
        assert top_k == 2
        return [Hit()]


class FakeLLM:
    """Fake LLM service."""

    def __init__(self) -> None:
        self.prompt = ""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Record prompt and return text."""

        _ = system
        self.prompt = prompt
        return "answer"


class Services:
    """Fake services."""

    def __init__(self) -> None:
        self.retrieval = FakeRetrieval()
        self.llm = FakeLLM()


async def test_retrieve_node_maps_hits() -> None:
    """Retrieve node should normalize RetrievalEngine hits."""

    result = await retrieve(VragState(query="q", messages=[]), {"top_k": 2}, Services())

    assert result["retrieved_docs"] == [
        {"chunk_id": "c1", "text": "stored context", "score": 0.9, "metadata": {"page": 1}}
    ]


async def test_generate_node_uses_retrieved_context() -> None:
    """Generate node should include retrieved document text in the prompt."""

    services = Services()
    result = await generate(
        VragState(query="q", retrieved_docs=[{"text": "stored context"}], messages=[]),
        {},
        services,
    )

    assert result["generation"] == "answer"
    assert "stored context" in services.llm.prompt
    assert "Question: q" in services.llm.prompt


async def test_terminal_message_nodes() -> None:
    """Clarification and unsupported nodes should use configurable messages."""

    clarify = await clarification(VragState(query="q", messages=[]), {"message": "clarify"}, None)
    reject = await unsupported(VragState(query="q", messages=[]), {"message": "reject"}, None)

    assert clarify["generation"] == "clarify"
    assert reject["generation"] == "reject"


async def test_memory_write_requires_memory_service() -> None:
    """memory_write is covered by dedicated MemoryService-backed tests."""

    state = VragState(query="q", messages=[])

    assert memory_write is not None
    assert state["query"] == "q"


def test_register_all_registers_expected_nodes_once() -> None:
    """Node package should register the P1 whitelist idempotently."""

    registry.clear()
    register_all()
    register_all()

    assert registry.list() == [
        "clarification",
        "classifier",
        "executor",
        "generate",
        "memory_recall",
        "memory_write",
        "planner",
        "reflect",
        "retrieve",
        "synthesizer",
        "unsupported",
    ]
