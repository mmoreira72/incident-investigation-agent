"""Triage entry + the business-signal report node.

triage() classifies the input and routes to one of two investigation paths that share
the same tail (notify_and_wait → decide):

  - structured GCP alert (JSON with incident fields)  → parse_alert → investigate
  - vague business signal (natural language)          → map_concern → fan-out → rank

build_report_signal() renders a report from the gather_context output so the shared
notify_and_wait/decide tail works for both paths.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json


# ── triage ───────────────────────────────────────────────────────────────────

_ALERT_HINTS = ("incident", "condition_name", "resource_type", "metric_type", "alertPolicy")


def _looks_like_alert(raw: str) -> bool:
    """A structured GCP alert is JSON carrying incident/condition fields."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(obj, dict):
        return False
    root = obj.get("incident", obj)
    return any(k in root or k in obj for k in _ALERT_HINTS)


def triage(state: dict) -> dict:
    """Decide which investigation path to run.

    Explicit wins: if the caller already set `concern` (+ `tenant`), it's a business
    signal. Otherwise sniff the raw input: alert JSON → alert path, else → signal path.
    """
    if state.get("concern"):
        route = "signal"
    elif _looks_like_alert(state.get("raw_signal", "") or state.get("alert_raw", "")):
        route = "alert"
    else:
        route = "signal"

    out: dict = {"route": route}
    # feed the alert path's expected input key
    if route == "alert" and not state.get("alert_raw"):
        out["alert_raw"] = state.get("raw_signal", "")
    return out


def route_triage(state: dict) -> str:
    """Conditional-edges path function → first node of the chosen path."""
    return "parse_alert" if state.get("route") == "alert" else "map_concern"


# ── business-signal report (mirrors incident_graph.build_report's contract) ────

def build_report_signal(state: dict) -> dict:
    """Render a markdown report from the gather_context ranking + change timeline.
    Sets `report`, plus `incident_id`/`service` so the shared notify_and_wait works."""
    tenant = state.get("tenant", "?")
    concern = state.get("concern", "?")
    ranked = state.get("ranked", []) or []
    hypothesis = state.get("hypothesis", "—")

    lines = [
        f"# Investigation — {tenant} / {concern}",
        "",
        f"**Signal:** {state.get('raw_signal', '')}",
        f"**Window:** {state.get('window', {})}",
        "",
        f"## Hypothesis",
        hypothesis,
        "",
        "## Ranked services (by deviation × change-correlation)",
    ]
    if ranked:
        for r in ranked:
            flag = " ⚠ change-correlated" if r.get("change_correlated") else ""
            lines.append(f"- **{r['service']}** — severity {r.get('severity', 0):.2f}{flag}")
    else:
        lines.append("- (no deviations found — consider widening the window)")

    # surface change timeline if any node collected it
    changes = []
    for entry in state.get("anomalies", []) or []:
        for svc, findings in entry.items():
            ev = (findings.get("changes", {}) or {}).get("evidence", {})
            for e in ev.get("events", []) or []:
                changes.append({"service": svc, **e})
    if changes:
        lines += ["", "## Change timeline (in window)"]
        for c in sorted(changes, key=lambda x: x.get("ts", "")):
            lines.append(f"- {c.get('ts','?')} · {c.get('service')} · {c.get('type','?')} · {c.get('ref','')}")

    report = "\n".join(lines)
    top = ranked[0]["service"] if ranked else "unknown"
    return {
        "report": report,
        "incident_id": f"{tenant}-{concern}",
        "service": top,
    }
