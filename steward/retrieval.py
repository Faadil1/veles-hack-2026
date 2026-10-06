"""Small BM25 retriever over the official HYPER-AI docs corpus (steward/docs/*.md).

Deterministic and dependency-free: the corpus is tiny, so lexical retrieval with section-level chunks is
enough, and every chunk keeps the source URL and section heading for citation.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"
_TOKEN = re.compile(r"[a-z0-9_]+")
_STOP = set(["a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "is", "are", "be", "with", "by", "as", "it", "this", "that", "from", "at", "you", "your", "how", "what", "do", "does", "can", "i", "me", "my", "we", "our"])


@dataclass(frozen=True)
class Chunk:
    doc_title: str
    source: str
    heading: str
    text: str
    fidelity: str

    @property
    def citation(self) -> str:
        return f"{self.doc_title} › {self.heading} ({self.source})"


_ALIASES = [(re.compile(r"hyper[\s_-]?ai\b"), "hyperai"), (re.compile(r"open[\s_-]connectors?"), "openconnectors"),
            (re.compile(r"application profile manager|\bapm\b"), "apm"), (re.compile(r"devicenodes?|device nodes?"), "devicenode")]


def _tokens(text: str) -> list[str]:
    text = text.lower()
    for pattern, canonical in _ALIASES:  # "HYPER-AI", "Hyper AI" and "HyperAI" must match each other
        text = pattern.sub(f" {canonical} ", text)
    return [t for t in _TOKEN.findall(text) if t not in _STOP]


def _parse(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        for line in front.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    chunks, heading, buf = [], meta.get("title", path.stem), []
    for line in body.splitlines():
        if line.startswith("#"):
            if "".join(buf).strip():
                chunks.append(Chunk(meta.get("title", path.stem), meta.get("source", ""), heading,
                                    "\n".join(buf).strip(), meta.get("fidelity", "")))
            heading, buf = line.lstrip("#").strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        chunks.append(Chunk(meta.get("title", path.stem), meta.get("source", ""), heading,
                            "\n".join(buf).strip(), meta.get("fidelity", "")))
    return chunks


class DocsIndex:
    def __init__(self, docs_dir: Path = DOCS_DIR, k1: float = 1.4, b: float = 0.75):
        self.chunks: list[Chunk] = []
        for path in sorted(docs_dir.glob("*.md")):
            self.chunks.extend(_parse(path))
        self.k1, self.b = k1, b
        self._tf = [Counter(_tokens(c.heading + " " + c.text)) for c in self.chunks]
        self._heading = [set(_tokens(c.heading)) for c in self.chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = sum(self._len) / max(len(self._len), 1)
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 4, min_score: float = 1.0) -> list[tuple[float, Chunk]]:
        q = _tokens(query)
        scored = []
        for i, tf in enumerate(self._tf):
            score = 0.0
            for term in q:
                if term not in tf:
                    continue
                f = tf[term]
                score += self._idf[term] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self._len[i] / self._avg))
            # A query term in the section heading is a strong topical signal even when the term is common
            # across the corpus (e.g. "What is HyperAI?" vs the heading "About HyperAI").
            score += 2.0 * len(set(q) & self._heading[i])
            if score >= min_score:
                scored.append((score, self.chunks[i]))
        scored.sort(key=lambda x: -x[0])
        return scored[:k]
