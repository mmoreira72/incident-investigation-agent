"""LangGraph wiring for gather_context (sub-graph with Send fan-out).

    map_concern --(Send x N)--> investigate_service --> rank_and_correlate -> END

Wire this sub-graph under the parent investigation graph's conditional edge from
`triage` (route == "gather_context"). Checkpointing via PostgresSaver is set up by the
parent; this module exposes a compilable sub-graph.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from .state import IncidentState
from .nodes import map_concern_to_funnel, investigate_service, rank_and_correlate


def build_gather_context(checkpointer=None):
    """Return the compiled gather_context sub-graph.

    `map_concern_to_funnel` is registered as the conditional-edges *path function*:
    it returns a list of Send objects, which LangGraph fans out to investigate_service.
    """
    g = StateGraph(IncidentState)

    g.add_node("investigate_service", investigate_service)
    g.add_node("rank", rank_and_correlate)

    # Entry: fan out from the concern. Using a pass-through entry node keeps the Send
    # path-function explicit and lets the parent enter at "map_concern".
    g.add_node("map_concern", lambda s: s)            # no-op; routing happens on its edges
    g.set_entry_point("map_concern")
    g.add_conditional_edges("map_concern", map_concern_to_funnel, ["investigate_service"])

    g.add_edge("investigate_service", "rank")          # rank runs after all Sends join
    g.add_edge("rank", END)

    return g.compile(checkpointer=checkpointer)


# Convenience for the parent graph:
#   graph.add_conditional_edges("triage", route, {"gather_context": "map_concern"})
# then embed build_gather_context() or inline these nodes.

if __name__ == "__main__":
    # Smoke test: compile + print structure (no backend calls).
    gc = build_gather_context()
    print("gather_context compiled OK")
    try:
        print(gc.get_graph().draw_ascii())
    except Exception:
        pass
