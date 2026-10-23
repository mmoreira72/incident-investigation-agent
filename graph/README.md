# graph/ — investigation graph (migrated out of `rag`)

These modules were moved here from `rag/src/` so the `rag` repo stays pure RAG (the
Se Liga chatbot) and the incident graph lives with the agent.

| File | Role |
|------|------|
| `incident_graph.py` | LangGraph: `parse_alert → investigate (tool loop) → build_report → notify_and_wait (interrupt) → decide` |
| `fetch_alert.py` | Convert a GCP alert policy → the graph's input format and run it |
| `list_alerts.py` | List GCP Cloud Monitoring alert policies |
| `investigate.py` | Folder/log investigation helper (uses the LLM client) |
| `tools.py` | LangChain `StructuredTool` wrappers over the investigation scripts |
| `skills_runtime.py` | Bridge: puts the cloudengineerskills `investigation-skills/*/scripts` on `sys.path` |
| `config.py` | Vendored minimal config (LLM endpoint/model, env-driven) |
| `llm_client.py` | Vendored thin OpenAI-compatible client |
| `rag.py` | **Retrieval boundary** — the seam to the `rag` repo (see below) |

## The RAG boundary (`rag.py`)

Skill retrieval (embeddings + reranker + pgvector) **is** the RAG core and stays in the
`rag` repo. `incident_graph.py` does `from rag import get_skills_with_confidence,
format_skills_for_prompt`, which resolves to `graph/rag.py` here — a port. By default it
returns `confidence="none"` (graph runs standalone). Wire the real retrieval via:

- **import mode:** `export RAG_SRC=/path/to/rag/src` → the port imports the real `rag.py`.
- **inject:** `from graph import rag; rag.configure(get_skills_with_confidence=...)`.
- **service mode (TODO):** point `RAG_MCP_URL`/`RAG_HTTP_URL` at the rag service.

## Env

| Var | Default | Purpose |
|-----|---------|---------|
| `LLM_BASE_URL` / `CHAT_MODEL` | `localhost:11434/v1` / `qwen3:14b` | LLM endpoint |
| `RAG_SRC` | — | path to `rag/src` to enable real skill retrieval |
| `INVESTIGATION_SCRIPTS_BASE` | cloudengineerskills path | where the investigation scripts live |

## Run

```bash
python graph/incident_graph.py --alert alert.json     # needs langgraph, langchain-openai
python graph/list_alerts.py                            # needs gcloud auth
```

## Unified graph (`unified_graph.py`)

One triage entry routes to two paths that share the `notify_and_wait → decide` tail:

```
triage ─route─▶ parse_alert ─▶ investigate ─▶ build_report ───────────────┐
       └route─▶ map_concern ─Send▶ investigate_service ─▶ rank ─▶ build_report_signal ─┤
                                                                                        ▼
                                                                   notify_and_wait ─▶ decide ─▶ END
```

- **alert path** — structured GCP alert (JSON) → the migrated `incident_graph` nodes.
- **signal path** — vague business signal ("conversions dropped") → `../gather_context/`
  (manifest: concern → funnel → `Send` fan-out → rank), then `build_report_signal`.
- `triage()` (in `triage.py`) sniffs the input: alert JSON vs natural language; an explicit
  `concern` in state forces the signal path.

Build/run:

```python
from graph.unified_graph import build_unified_graph
app = build_unified_graph()                 # needs langgraph + langchain-openai
# business signal:
app.invoke({"raw_signal": "conversions dropped", "tenant": "acme",
            "concern": "conversions", "window": {...}})
# or a GCP alert:
app.invoke({"raw_signal": open("alert.json").read()})
```
