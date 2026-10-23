"""Retrieval boundary (port to the `rag` repo).

This is the seam created by the split: skill retrieval (embeddings + reranker +
pgvector) IS the RAG core and stays in the `rag` repo — "rag só rag". The investigation
graph only needs the *result*, so it imports `get_skills_with_confidence` /
`format_skills_for_prompt` from here. `incident_graph.py` does `from rag import ...`,
which resolves to this module (a sibling in the graph/ package).

Default behavior: returns confidence="none" (no skill context) so the graph runs
standalone. Wire the real retrieval one of three ways:

  1. import mode  — set RAG_SRC=/path/to/rag/src; this module imports the real rag.py.
  2. service mode — set RAG_MCP_URL / RAG_HTTP_URL; call the rag service over the wire.
  3. inject       — call configure(get_skills_with_confidence=<callable>) at startup.

format_skills_for_prompt() is implemented locally (it's pure formatting) so prompts are
correct regardless of how retrieval is wired.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional


@dataclass
class RetrievedSkill:
    name: str
    content: str
    score: float


@dataclass
class SkillRetrievalResult:
    skills: list[RetrievedSkill] = field(default_factory=list)
    confidence: Literal["high", "medium", "low", "none"] = "none"
    top_score: float = 0.0
    gap: float = 0.0
    candidate_count: int = 0


# --- pluggable implementation -------------------------------------------------

_impl: Optional[Callable[[str], SkillRetrievalResult]] = None


def configure(get_skills_with_confidence: Callable[[str], SkillRetrievalResult]) -> None:
    """Inject a real retrieval function (inject mode)."""
    global _impl
    _impl = get_skills_with_confidence


def _try_import_mode() -> Optional[Callable[[str], SkillRetrievalResult]]:
    """If RAG_SRC points at the rag repo's src/, use its real retrieval."""
    rag_src = os.getenv("RAG_SRC")
    if not rag_src or not os.path.isdir(rag_src):
        return None
    if rag_src not in sys.path:
        sys.path.insert(0, rag_src)
    try:
        import importlib
        real = importlib.import_module("rag")   # the real rag/src/rag.py
        return real.get_skills_with_confidence
    except Exception as exc:  # noqa: BLE001
        print(f"[retrieval] RAG_SRC import failed ({exc}); using no-skill stub", flush=True)
        return None


def get_skills_with_confidence(query: str) -> SkillRetrievalResult:
    """Return retrieved skills + confidence. Order: injected impl → import mode → stub."""
    fn = _impl or _try_import_mode()
    if fn is not None:
        return fn(query)
    # TODO service mode: call RAG_MCP_URL / RAG_HTTP_URL here.
    return SkillRetrievalResult(confidence="none")   # standalone-safe default


def format_skills_for_prompt(result: SkillRetrievalResult) -> str:
    """Pure formatting (mirrors rag/src/rag.py). Empty string when confidence is none."""
    if result.confidence == "none" or not result.skills:
        return ""
    if result.confidence == "high":
        sk = result.skills[0]
        return f"[skill: {sk.name}, relevance: {sk.score:.2f}]\n\n{sk.content}"
    header = (
        f"[WARNING: multiple potentially relevant skills retrieved "
        f"(confidence={result.confidence}). Review all before responding.]\n\n"
    )
    blocks = [f"[skill: {sk.name}, relevance: {sk.score:.2f}]\n\n{sk.content}" for sk in result.skills]
    return header + "\n\n---\n\n".join(blocks)
