"""Cascade intent classifier tests."""


from app.core.graph.nodes.classifier import classify
from app.core.graph.state import Intent, VragState


class FakeEmbedder:
    """Embed texts from a deterministic map."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return known vectors or a low-confidence fallback."""

        return [self.vectors.get(text, [0.0, 0.0, 0.0]) for text in texts]


class FakeLLM:
    """Fake classifier LLM."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.prompts: list[str] = []

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Record prompt and return JSON classification."""

        self.prompts.append(f"{system}\n{prompt}")
        return self.raw


class Services:
    """Fake graph services."""

    def __init__(self, embedder: FakeEmbedder, llm: FakeLLM) -> None:
        self.embedder = embedder
        self.llm = llm


def _services(
    vectors: dict[str, list[float]] | None = None,
    llm_raw: str = '{"intent": "knowledge_qa", "confidence": 0.77, "reason": "doc"}',
) -> Services:
    base = {
        "你好": [1.0, 0.0, 0.0],
        "你是谁": [1.0, 0.0, 0.0],
        "嗨": [1.0, 0.0, 0.0],
        "产品怎么配置": [0.0, 1.0, 0.0],
        "文档里说": [0.0, 1.0, 0.0],
        "请解释": [0.0, 1.0, 0.0],
        "帮我看看": [0.0, 0.0, 1.0],
        "那个东西": [0.0, 0.0, 1.0],
    }
    if vectors:
        base.update(vectors)
    return Services(FakeEmbedder(base), FakeLLM(llm_raw))


async def test_rule_match_short_circuits_to_unsupported() -> None:
    """Sensitive rule matches should not call semantic or LLM routing."""

    result = await classify(
        VragState(query="帮我删除账号", messages=[]),
        {},
        _services(),
    )

    assert result["intent"] is Intent.UNSUPPORTED
    assert result["confidence"] == 1.0
    assert result["route_trace"]["reason"] == "rule"


async def test_high_confidence_semantic_route_is_direct() -> None:
    """High semantic confidence should route directly."""

    result = await classify(
        VragState(query="配置说明", messages=[]),
        {},
        _services({"配置说明": [0.0, 1.0, 0.0]}),
    )

    assert result["intent"] is Intent.KNOWLEDGE_QA
    assert result["route_trace"]["reason"] == "semantic-direct"


async def test_mid_confidence_semantic_route_uses_llm() -> None:
    """Mid confidence should ask the LLM for final intent."""

    services = _services(
        {"需要说明吗": [0.65, 0.76, 0.0]},
        '{"intent": "chitchat", "confidence": 0.72, "reason": "greeting"}',
    )

    result = await classify(VragState(query="需要说明吗", messages=[]), {}, services)

    assert result["intent"] is Intent.CHITCHAT
    assert result["confidence"] == 0.72
    assert result["route_trace"]["reason"] == "semantic-then-llm"
    assert services.llm.prompts


async def test_low_confidence_routes_to_clarification() -> None:
    """Very low semantic confidence should request clarification."""

    result = await classify(
        VragState(query="???", messages=[]),
        {},
        _services({"???": [0.0, 0.0, 0.0]}),
    )

    assert result["intent"] is Intent.CLARIFICATION
    assert result["route_trace"]["reason"] == "low-confidence-clarify"
