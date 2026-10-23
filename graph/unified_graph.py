"""Unified investigation graph — one triage entry, two paths, shared tail.

    triage ─route─▶ parse_alert ─▶ investigate ─▶ build_report ───────────────┐
           └route─▶ map_concern ─Send▶ investigate_service ─▶ rank ─▶ build_report_signal ─┤
                                                                                            ▼
                                                                       notify_and_wait ─▶ decide ─▶ END

- alert path  : the migrated incident_graph nodes (structured GCP alert)
- signal path : gather_context (manifest-driven business concern → funnel → fan-out → rank)
- shared tail : notify_and_wait (interrupt → engineer) → decide

Heavy imports (langchain/langgraph) happen inside build_unified_graph so this module
stays importable for inspection without the runtime deps installed.
"""
from __future__ import annotations
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # graph/ on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root (gather_context)


def build_unified_graph(checkpointer=None):
    from langgraph.graph import StateGraph, END

    from unified_state import UnifiedState
    from triage import triage, route_triage, build_report_signal
    # alert path (migrated)
    from incident_graph import parse_alert, investigate, build_report as build_report_alert, \
        notify_and_wait, decide
    # business-signal path (manifest-driven)
    from gather_context.nodes import (
        map_concern_to_funnel, investigate_service, rank_and_correlate,
    )

    g = StateGraph(UnifiedState)

    g.add_node("triage", triage)

    # alert path
    g.add_node("parse_alert", parse_alert)
    g.add_node("investigate", investigate)
    g.add_node("build_report", build_report_alert)

    # signal path
    g.add_node("map_concern", lambda s: s)            # no-op; Send fan-out on its edges
    g.add_node("investigate_service", investigate_service)
    g.add_node("rank", rank_and_correlate)
    g.add_node("build_report_signal", build_report_signal)

    # shared tail
    g.add_node("notify_and_wait", notify_and_wait)
    g.add_node("decide", decide)

    g.set_entry_point("triage")
    g.add_conditional_edges("triage", route_triage, {
        "parse_alert": "parse_alert",
        "map_concern": "map_concern",
    })

    # alert path edges
    g.add_edge("parse_alert", "investigate")
    g.add_edge("investigate", "build_report")
    g.add_edge("build_report", "notify_and_wait")

    # signal path edges (map_concern_to_funnel returns a list of Send → investigate_service)
    g.add_conditional_edges("map_concern", map_concern_to_funnel, ["investigate_service"])
    g.add_edge("investigate_service", "rank")
    g.add_edge("rank", "build_report_signal")
    g.add_edge("build_report_signal", "notify_and_wait")

    # tail
    g.add_edge("notify_and_wait", "decide")
    g.add_edge("decide", END)

    return g.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    gc = build_unified_graph()
    print("unified graph compiled OK")
    try:
        print(gc.get_graph().draw_ascii())
    except Exception:
        pass
