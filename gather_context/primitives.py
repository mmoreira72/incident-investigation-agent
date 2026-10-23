"""Generic primitives — the 'generic scripts' that are missing today.

These are NOT per-case scripts. Each is parameterized entirely by the manifest:
the service / query / log string is read from `service_cfg`, never hardcoded. One
implementation, every tenant.

Status: SCAFFOLD. Each returns a typed Finding with status="not_implemented" so the
graph runs end-to-end today; fill the bodies against the real backends. Wire them to
the existing cloudengineerskills scripts where possible:
  - check_*_deviation / traffic  -> fetch_timeseries.py  (GCP Monitoring MQL) or Datadog API
  - check_slow_queries           -> fetch_logs.py        (GCP Cloud Logging, no severity filter)
  - check_recent_changes         -> list_revisions.py (Cloud Run) + ArgoCD + Spacewalk + FeatureFlag
NB: per cloudengineerskills convention, fetch logs WITHOUT a severity filter (OOM is DEFAULT).
"""
from __future__ import annotations
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Finding:
    kind: str                      # "latency" | "error_rate" | "traffic" | "slow_sql" | "changes"
    service: str
    status: str = "not_implemented"   # "ok" | "deviation" | "no_data" | "not_implemented"
    deviation: Optional[float] = None # signed % vs baseline (e.g. +0.42 = +42%)
    severity: float = 0.0             # 0..1 for ranking
    evidence: dict[str, Any] = field(default_factory=dict)  # raw values, query used, log links

    def dict(self) -> dict:
        return asdict(self)


def _src(service_cfg: dict, sli: str, prefer: str = "gcp_monitoring") -> Optional[str]:
    """Pull the metric source string for an SLI from the manifest, honoring the
    tenant's preferred metrics backend. Returns None if not declared (a real gap)."""
    spec = (service_cfg.get("slis") or {}).get(sli)
    if not spec:
        return None
    if isinstance(spec, str):
        return spec
    return spec.get(prefer) or next(iter(spec.values()), None)


# --- the five primitives -----------------------------------------------------

def check_latency_deviation(service_cfg: dict, window, baseline_window, prefer="gcp_monitoring") -> Finding:
    """Compare p95 latency in `window` vs the seasonal `baseline_window`.
    Source query comes from service_cfg['slis']['latency_p95']."""
    query = _src(service_cfg, "latency_p95", prefer)
    if not query:
        return Finding("latency", service_cfg["name"], status="no_data",
                       evidence={"reason": "no latency_p95 SLI in manifest"})
    # TODO: run `query` (GCP Monitoring MQL via fetch_timeseries, or Datadog), compute p95
    #       for window and baseline_window, set deviation/severity.
    return Finding("latency", service_cfg["name"], evidence={"query": query})


def check_error_rate(service_cfg: dict, window, baseline_window, prefer="gcp_monitoring") -> Finding:
    query = _src(service_cfg, "error_rate", prefer)
    if not query:
        return Finding("error_rate", service_cfg["name"], status="no_data",
                       evidence={"reason": "no error_rate SLI in manifest"})
    # TODO: good/total ratio for window vs baseline.
    return Finding("error_rate", service_cfg["name"], evidence={"query": query})


def check_traffic_volume(service_cfg: dict, window, baseline_window, prefer="gcp_monitoring") -> Finding:
    """Request volume vs seasonal baseline — a traffic *drop* often is the symptom
    (fewer searches/bookings), not an error spike."""
    query = _src(service_cfg, "error_rate", prefer)  # reuse total-request source if present
    return Finding("traffic", service_cfg["name"], evidence={"query": query})


def check_slow_queries(datastore_cfg: Optional[dict], window) -> Optional[Finding]:
    """Slow query log for the service's datastore. Source from datastore_cfg['slow_query'].
    Returns None if the service has no datastore. Note: legacy MariaDB ships NO slow log
    (see GAPS) and Atlas routes through profiler/Datadog, not GCP logging."""
    if not datastore_cfg:
        return None
    src = datastore_cfg.get("slow_query")
    if not src or src == "NONE":
        return Finding("slow_sql", datastore_cfg.get("name", "?"), status="no_data",
                       evidence={"reason": f"no slow-query source ({src})"})
    # TODO: fetch_logs.py against `src` (GCP Cloud Logging) or Atlas profiler.
    return Finding("slow_sql", datastore_cfg.get("name", "?"), evidence={"source": src})


def check_recent_changes(service_cfg: dict, window, change_sources: dict) -> Finding:
    """HIGHEST-ROI primitive. Build the change timeline for this service in `window`:
    deploys (ArgoCD/Cloud Run revisions/Spacewalk), feature toggles (FeatureFlag),
    config (Terragrunt apply). ~80% of 'conversion dropped' coincides with one of these.
    See changes.py for the aggregation helper."""
    from .changes import collect_changes
    events = collect_changes(service_cfg, window, change_sources)
    sev = 0.6 if events else 0.0   # presence of a recent change is itself signal
    return Finding("changes", service_cfg["name"],
                   status="deviation" if events else "ok",
                   severity=sev, evidence={"events": events})
