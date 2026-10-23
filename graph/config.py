"""Minimal config for the investigation graph (vendored out of rag/src/config.py).

Only the knobs the graph needs. Everything is env-driven so the same code runs against
local LM Studio / Ollama / a remote GPU server without edits.
"""
import os

# LLM (OpenAI-compatible endpoint: Ollama / LM Studio / vLLM)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3:14b")

# Models to pre-load (warmup) — comma-separated; defaults to CHAT_MODEL
WARMUP_MODELS = [m.strip() for m in os.getenv("WARMUP_MODELS", CHAT_MODEL).split(",") if m.strip()]

# Skill-retrieval confidence thresholds (used by the retrieval port if wired to the
# real rag service; harmless defaults otherwise).
SKILL_ABSOLUTE_MIN_SCORE = float(os.getenv("SKILL_ABSOLUTE_MIN_SCORE", "0.45"))
SKILL_AUTO_SELECT_SCORE = float(os.getenv("SKILL_AUTO_SELECT_SCORE", "0.70"))
