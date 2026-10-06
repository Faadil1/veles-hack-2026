import pytest

from steward.guardrail import classify
from steward.retrieval import DocsIndex
from tests.harness import Harness

DOCS = DocsIndex()

IN_SCOPE = [
    "What is HyperAI?", "What is HYPER-AI?", "What are Open Connectors?", "hello", "What can you do?",
    "Create a deployment YAML for a service using the nginx Docker image", "delete app.yaml", "undo",
    "check demo/app.yaml", "How do I deploy a workflow?", "What does the application profile manager do?",
    "Fix it so it runs on arm64", "explain the qos section", "Which architectures can a device app target?",
]
OFF_TOPIC = [
    "What is the weather today?", "Who won the football match?", "Give me a recipe for paella",
    "Tell me a joke", "What's the bitcoin price?", "What is the capital of France?", "write me a poem about cats",
]


@pytest.mark.parametrize("text", IN_SCOPE)
def test_in_scope(text):
    assert classify(text, DOCS).in_scope, text


@pytest.mark.parametrize("text", OFF_TOPIC)
def test_off_topic(text):
    assert not classify(text, DOCS).in_scope, text


def test_short_follow_up_is_allowed_in_conversation_but_off_topic_still_refused():
    assert classify("and the other one?", DOCS, in_conversation=True).in_scope
    assert not classify("and the weather?", DOCS, in_conversation=True).in_scope


async def test_off_topic_is_refused_without_any_model_call():
    from steward.llm import ScriptedLLM
    llm = ScriptedLLM([])  # any model call would raise
    h = Harness({}, llm=llm)
    turn = await h.say("What is the weather today?")
    assert "HYPER-AI" in turn.text and turn.actions == [] and llm.calls == []
