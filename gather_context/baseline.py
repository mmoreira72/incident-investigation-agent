"""Seasonal baseline + the Datadog-anomaly shortcut.

Check #1 from the design: do NOT compare flat. Conversion drops naturally overnight
and on weekdays. Compare against the SAME window, SAME weekday, prior weeks. Where
Datadog already runs anomaly/forecast monitors, prefer asking "is a monitor firing?"
over recomputing the baseline ourselves; roll our own only where DD doesn't cover
(e.g. slow query log).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from .state import Window


def seasonal_baseline(window: Window, weeks_back: int = 4) -> list[Window]:
    """Return the same clock window on the same weekday for the previous `weeks_back`
    weeks. The primitive averages over these to get a seasonal expectation."""
    start = datetime.fromisoformat(window["start"])
    end = datetime.fromisoformat(window["end"])
    out: list[Window] = []
    for w in range(1, weeks_back + 1):
        out.append(Window(
            start=(start - timedelta(weeks=w)).isoformat(),
            end=(end - timedelta(weeks=w)).isoformat(),
        ))
    return out


def datadog_anomaly_firing(service_cfg: dict, observability: dict) -> dict | None:
    """Shortcut: if the tenant uses Datadog anomaly/forecast monitors and one is firing
    for this service, return it — cheaper and more accurate than a home-grown baseline.
    Returns None if DD isn't the anomaly source or no monitor matches.

    TODO: call Datadog Monitors API filtered by service tag; return {monitor, state, ...}.
    GAP: which services actually have DD monitors is currently unknown (see GAPS gap #10).
    """
    if observability.get("anomaly_monitors") != "datadog":
        return None
    return None  # not_implemented
