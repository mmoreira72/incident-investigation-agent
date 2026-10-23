"""Unified state for the triaged graph.

Superset of:
  - the alert-driven IncidentState (graph/incident_graph.py)
  - the business-signal gather_context state (gather_context/state.py)

Both families of nodes only touch their own keys, so a single dict carries both.
`anomalies` keeps the operator.add reducer so gather_context's Send fan-out accumulates.
"""
from __future__ import annotations
from typing import TypedDict, Annotated, Literal, Any
import operator


class UnifiedState(TypedDict, total=False):
    # ── shared input / routing ──────────────────────────────────────────────
    raw_signal: str                 # natural-language signal OR raw alert JSON
    route: Literal["alert", "signal"]

    # ── alert path (from incident_graph.IncidentState) ──────────────────────
    alert_raw: str
    incident_id: str
    project: str
    service: str
    resource_type: str
    metric_type: str
    condition_type: str
    region: str
    alert_ts: str
    condition_name: str
    alert_url: str
    error_logs: str
    metrics_data: str
    release_found: bool
    release_id: str
    release_ts: str
    release_type: str
    release_logs: str
    skill_retrievals: list
    scripts_invoked: list
    analysis_log_url: str
    investigation_result: str

    # ── business-signal path (from gather_context.state.IncidentState) ──────
    tenant: str
    concern: str
    window: dict
    baseline_window: dict
    anomalies: Annotated[list[dict], operator.add]
    change_timeline: list[dict]
    ranked: list[dict]
    hypothesis: str

    # ── shared tail ─────────────────────────────────────────────────────────
    report: str
    engineer_response: str
    decision: Literal["rollback", "escalate", "close", "monitor"]
