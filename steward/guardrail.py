"""Topical guardrail: keep Hyperion on HYPER-AI and the user's workspace.

Runs before any model call, so irrelevant requests cost no tokens on the metered team server and always get the
same answer. Biased toward letting requests through: anything that mentions the workspace, files, profiles,
deployment, the platform, or the assistant itself is in scope. Only requests with no such signal and a weak or
missing match in the official docs are declined.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .retrieval import DocsIndex

IN_SCOPE_WORDS = re.compile(
    r"\b(hyper[\s-]?ai|hyperion|steward|ide|workspace|file|files|folder|folders|yaml|yml|profile|profiles|app|apps|"
    r"application|applications|deploy|deployment|deployed|workflow|workflows|container|docker|image|kubernetes|k8s|"
    r"helm|device|devices|edge|cloud|iot|continuum|node|nodes|cluster|esp32|android|apk|native|validate|validation|"
    r"valid|invalid|schema|dsl|spec|run|runs|running|create|edit|delete|remove|rename|fix|undo|revert|check|write|read|open|show|"
    r"port|ports|qos|latency|cpu|memory|gpu|architecture|arm64|amd64|x86_64|nginx|service|services|connector|"
    r"connectors|orchestration|swarm|wizard|dashboard|metrics|template|templates|example|cookbook|tutorial)\b", re.I)
SMALL_TALK = re.compile(
    r"^\s*(hi|hello|hey|bonjour|salut|hola|thanks|thank you|merci|gracias|ok|okay|good (morning|evening|afternoon)|"
    r"who are you|what are you|what can you do|help|how can you help( me)?|what do you do)\b", re.I)
OFF_TOPIC = re.compile(
    r"\b(weather|forecast|temperature outside|football|soccer|basketball|match score|who won|recipe|cook|cooking|"
    r"stock price|bitcoin price|crypto price|horoscope|joke|poem|song|lyrics|movie|celebrity|election|president|"
    r"politics|news today|capital of|translate this)\b", re.I)
PATH_LIKE = re.compile(r"[\w.-]+\.(ya?ml|json|md|txt|py|sh)\b|[\w.-]+/[\w./-]+")

REFUSAL = ("I'm Hyperion, the assistant for the HYPER-AI IDE, so I can only help with HYPER-AI and your workspace: "
           "questions about the platform, and creating, checking, fixing or deleting application profiles and files. "
           "Try something like “Create a device app for the nginx image” or “What are Open Connectors?”.")


@dataclass(frozen=True)
class Verdict:
    in_scope: bool
    reason: str


def classify(text: str, docs: DocsIndex, docs_min_score: float = 5.0, in_conversation: bool = False) -> Verdict:
    if OFF_TOPIC.search(text) and not PATH_LIKE.search(text) and not re.search(r"hyper[\s-]?ai|hyperion", text, re.I):
        return Verdict(False, "explicitly_off_topic")
    if SMALL_TALK.search(text):
        return Verdict(True, "small_talk_about_assistant")
    if PATH_LIKE.search(text):
        return Verdict(True, "mentions_a_path")
    if IN_SCOPE_WORDS.search(text):
        return Verdict(True, "platform_or_workspace_vocabulary")
    if in_conversation and len(text.split()) <= 12:
        return Verdict(True, "short_follow_up_in_conversation")
    hits = docs.search(text, k=1, min_score=docs_min_score)
    if hits:
        return Verdict(True, f"strong_docs_match:{hits[0][1].heading}")
    return Verdict(False, "no_platform_signal")
