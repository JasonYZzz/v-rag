"""Cascade intent classifier: rules -> semantic route -> LLM fallback."""

import json
from typing import Any

from app.core.graph.state import Intent, VragState

DIRECT_THRESHOLD = 0.85
LOW_THRESHOLD = 0.60

RULES: dict[Intent, list[str]] = {
    Intent.UNSUPPORTED: ["密码", "信用卡", "删除账号"],
}

INTENT_EXEMPLARS: dict[Intent, list[str]] = {
    Intent.CHITCHAT: ["你好", "你是谁", "嗨"],
    Intent.KNOWLEDGE_QA: ["产品怎么配置", "文档里说", "请解释"],
    Intent.CLARIFICATION: ["帮我看看", "那个东西"],
}


def _rule_route(query: str) -> Intent | None:
    for intent, keywords in RULES.items():
        if any(keyword in query for keyword in keywords):
            return intent
    return None


async def _semantic_route(query: str, embedder: Any) -> tuple[Intent | None, float]:
    """Route by cosine similarity to intent exemplar prototypes."""

    import numpy as np

    qv = np.array((await embedder.embed([query]))[0])
    best_intent: Intent | None = None
    best_score = 0.0
    for intent, exemplars in INTENT_EXEMPLARS.items():
        evs = np.array(await embedder.embed(exemplars))
        proto = evs.mean(axis=0)
        denom = float(np.linalg.norm(qv) * np.linalg.norm(proto) + 1e-9)
        score = float(qv @ proto / denom)
        if score > best_score:
            best_intent = intent
            best_score = score
    return best_intent, best_score


async def _llm_route(query: str, llm: Any) -> tuple[Intent, float]:
    """Ask the LLM to classify as a fallback."""

    options = ", ".join(intent.value for intent in Intent)
    prompt = (
        f"Classify the user query into one of: {options}. "
        'Reply JSON {"intent": "...", "confidence": 0.0-1.0, "reason": "..."}.\n'
        f"Query: {query}"
    )
    raw = await llm.complete(prompt, system="You are an intent classifier.")
    data = json.loads(raw)
    return Intent(data["intent"]), float(data.get("confidence", 0.5))


async def classify(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Classify the user query and write route_trace."""

    _ = config
    query = state["query"]
    trace: dict[str, Any] = {}

    rule_intent = _rule_route(query)
    trace["rule_result"] = rule_intent.value if rule_intent else None
    if rule_intent:
        return _finish(rule_intent, 1.0, trace, "rule")

    semantic_intent, semantic_score = await _semantic_route(query, services.embedder)
    trace["semantic_result"] = (
        semantic_intent.value if semantic_intent else None,
        semantic_score,
    )
    if semantic_intent and semantic_score >= DIRECT_THRESHOLD:
        return _finish(semantic_intent, semantic_score, trace, "semantic-direct")

    if semantic_intent and semantic_score >= LOW_THRESHOLD:
        llm_intent, llm_score = await _llm_route(query, services.llm)
        trace["llm_result"] = (llm_intent.value, llm_score)
        return _finish(llm_intent, llm_score, trace, "semantic-then-llm")

    trace["llm_result"] = None
    return _finish(Intent.CLARIFICATION, semantic_score, trace, "low-confidence-clarify")


def _finish(
    intent: Intent, confidence: float, trace: dict[str, Any], reason: str
) -> dict[str, Any]:
    trace.update(final_intent=intent.value, confidence=confidence, reason=reason)
    return {"intent": intent, "confidence": confidence, "route_trace": trace}
