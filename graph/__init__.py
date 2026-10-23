"""Investigation graph — migrated out of the `rag` repo so that rag stays pure RAG
(the Se Liga chatbot) and the incident graph lives with the agent.

The modules here keep flat imports (`from config import ...`, `from rag import ...`,
`from tools import ...`) resolving to siblings in this package; we add this dir to
sys.path on import so both `import graph.incident_graph` and `python graph/incident_graph.py`
work without rewriting every import.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
