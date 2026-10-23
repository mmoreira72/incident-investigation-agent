"""Thin OpenAI-compatible LLM client (vendored from rag/src/llm_client.py).

Used by investigate.py. The graph proper uses langchain_openai.ChatOpenAI directly;
this is the lower-level helper for streaming/raw calls.
"""
from openai import OpenAI

from config import LLM_BASE_URL, CHAT_MODEL, WARMUP_MODELS

client = OpenAI(base_url=LLM_BASE_URL, api_key="ollama")


def chat(messages: list[dict], stream: bool = True):
    return client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
        stream=stream,
    )


def warmup_llm_models() -> None:
    """Pre-load configured LLM models into VRAM (avoids first-request load latency)."""
    for model in WARMUP_MODELS:
        try:
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "oi"}],
                max_tokens=1,
                stream=False,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] warmup falhou para {model}: {exc}", flush=True)
