"""Shared graph state. Mirrors the cloudengineerskills IncidentState pattern:
a single TypedDict, list fields merged with operator.add so parallel Sends accumulate.
"""
from __future__ import annotations
from typing import TypedDict, Annotated, Any
import operator


class Window(TypedDict):
    start: str   # ISO8601
    end: str


class IncidentState(TypedDict, total=False):
    # --- inputs (set by triage / caller) ---
    tenant: str                       # "acme" | "tenant-b" | ...
    concern: str                      # "conversions" | "payments_failing" | ...
    raw_signal: str                   # the vague business report, verbatim
    window: Window                    # investigation window (6h .. 7d)
    baseline_window: Window           # seasonal comparison window

    # --- accumulated by fan-out (operator.add) ---
    anomalies: Annotated[list[dict], operator.add]   # one {service: findings} per Send
    change_timeline: list[dict]                       # deploys/toggles/config in window

    # --- produced by rank_and_correlate ---
    ranked: list[dict]
    hypothesis: str


# Payload passed to each investigate_service Send (not merged into parent except via return)
class ServiceTask(TypedDict, total=False):
    tenant: str
    service_cfg: dict
    window: Window
    baseline_window: Window
