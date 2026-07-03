"""Graph state contract tests."""

from app.core.graph.state import Intent, VragState


def test_intent_taxonomy_has_seven_values() -> None:
    """Intent enum should expose the P1-A taxonomy."""

    assert {intent.value for intent in Intent} == {
        "chitchat",
        "knowledge_qa",
        "multimodal_doc",
        "tool_action",
        "complex_task",
        "clarification_needed",
        "unsupported_or_rejected",
    }


def test_vrag_state_can_be_constructed_incrementally() -> None:
    """State should allow partial node patches through total=False."""

    state: VragState = {
        "query": "产品怎么配置",
        "intent": Intent.KNOWLEDGE_QA,
        "confidence": 0.91,
        "messages": [],
    }

    assert state["query"] == "产品怎么配置"
    assert state["intent"] is Intent.KNOWLEDGE_QA
