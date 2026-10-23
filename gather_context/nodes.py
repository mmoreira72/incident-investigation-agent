"""The gather_context nodes.

Flow:  map_concern  --Send fan-out-->  investigate_service (xN parallel)  -->  rank_and_correlate
"""
from __future__ import annotations
from typing import Any

from .manifest import load_manifest, funnel_for, service_cfg, change_sources
from .baseline import seasonal_baseline, datadog_anomaly_firing
from .primitives import (
    check_latency_deviation, check_error_rate, check_traffic_volume,
    check_slow_queries, check_recent_changes,
)


def map_concern_to_funnel(state: dict) -> list:
    """'conversão baixa' -> load the relevant subgraph from the tenant manifest and
    fan out one investigate_service per funnel service. Returns a list of Send (imported
    lazily so this module stays importable without langgraph installed)."""
    from langgraph.constants import Send

    manifest = load_manifest(state["tenant"])
    funnel = funnel_for(manifest, state["concern"])
    window = state["window"]
    baseline = state.get("baseline_window") or (seasonal_baseline(window)[0] if window else None)

    return [
        Send("investigate_service", {
            "tenant": state["tenant"],
            "service_cfg": service_cfg(manifest, svc),
            "window": window,
            "baseline_window": baseline,
        })
        for svc in funnel
    ]


def investigate_service(task: dict) -> dict:
    """Run the generic primitives for one service. Returns {"anomalies": [...]} which is
    merged into parent state via operator.add."""
    cfg = task["service_cfg"]
    window, baseline = task["window"], task.get("baseline_window")
    manifest = load_manifest(task["tenant"])

    findings = {
        "latency":  check_latency_deviation(cfg, window, baseline).dict(),
        "errors":   check_error_rate(cfg, window, baseline).dict(),
        "traffic":  check_traffic_volume(cfg, window, baseline).dict(),
        "changes":  check_recent_changes(cfg, window, change_sources(manifest)).dict(),
    }
    sql = check_slow_queries(cfg.get("datastore_cfg"), window)
    if sql is not None:
        findings["slow_sql"] = sql.dict()

    return {"anomalies": [{cfg["name"]: findings}]}


def rank_and_correlate(state: dict) -> dict:
    """Rank deviations by severity and cross them with the change timeline. A deviation
    that lines up with a recent change in the same service ranks highest — that's the
    hypothesis. (Statistics are secondary to change correlation.)"""
    ranked = []
    for entry in state.get("anomalies", []):
        for svc, findings in entry.items():
            has_change = findings.get("changes", {}).get("status") == "deviation"
            sev = max((f.get("severity", 0.0) for f in findings.values() if isinstance(f, dict)), default=0.0)
            if has_change:
                sev = min(1.0, sev + 0.3)   # change correlation boosts rank
            ranked.append({"service": svc, "severity": round(sev, 3),
                           "change_correlated": has_change, "findings": findings})

    ranked.sort(key=lambda r: r["severity"], reverse=True)
    top = ranked[0] if ranked else None
    hypothesis = (
        f"Most likely origin: {top['service']}"
        + (" (correlated with a recent change)" if top and top["change_correlated"] else "")
        if top else "No clear deviation — escalate / widen window."
    )
    return {"ranked": ranked, "hypothesis": hypothesis}
