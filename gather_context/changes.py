"""Change correlation — the highest-ROI primitive.

Check #2 from the design: 'what deviates from normal' almost always coincides with a
change. Before any statistics, build the change timeline in the window and overlay it
on the KPI curve. ~80% of 'conversion dropped' is a deploy or toggle from a few hours
ago.

For Acme the change feed is fragmented across FIVE sources (see GAPS gap #6):
  deploys.gke        -> ArgoCD sync events (argocd-apps, per platform)
  deploys.cloud_run  -> Cloud Run revision create events (list_revisions.py)
  deploys.legacy_vm  -> Spacewalk package/config rollouts
  feature_toggles    -> FeatureFlag datafile pushes (the featureflag-webhook Cloud Run)
  config             -> GitHub Actions / Terragrunt applies
This module aggregates them into one normalized timeline.
"""
from __future__ import annotations
from typing import Any
from .state import Window


def collect_changes(service_cfg: dict, window: Window, change_sources: dict) -> list[dict]:
    """Return a normalized, time-ordered list of change events touching this service
    within `window`. Each event: {ts, type, source, ref, detail}.

    Status: SCAFFOLD — each collector is a stub. Implement the ones the service uses
    based on service_cfg['runtime'] and deploy_source, plus tenant-wide toggles."""
    events: list[dict] = []
    runtime = service_cfg.get("runtime")
    deploy_source = service_cfg.get("deploy_source", "")

    # 1) deploys for this service's runtime
    if runtime == "gke" or deploy_source.startswith("argocd:"):
        events += _argocd_syncs(deploy_source, window, change_sources)
    if runtime == "cloud-run":
        events += _cloud_run_revisions(service_cfg, window)
    if runtime in ("vm", "legacy"):
        events += _spacewalk_rollouts(service_cfg, window, change_sources)

    # 2) tenant-wide feature toggles (apply to any service — esp. conversions)
    events += _featureflag_pushes(window, change_sources)

    # 3) IaC config applies that touched the service's project
    events += _terragrunt_applies(service_cfg, window, change_sources)

    return sorted(events, key=lambda e: e.get("ts", ""))


# --- collectors (stubs) ------------------------------------------------------

def _argocd_syncs(deploy_source: str, window: Window, cs: dict) -> list[dict]:
    # TODO: query ArgoCD API / Application sync history for `deploy_source` in window.
    return []


def _cloud_run_revisions(service_cfg: dict, window: Window) -> list[dict]:
    # TODO: reuse cloudengineerskills list_revisions.py — revisions created in window.
    return []


def _spacewalk_rollouts(service_cfg: dict, window: Window, cs: dict) -> list[dict]:
    # TODO: Spacewalk action history for the host(s) backing this service.
    return []


def _featureflag_pushes(window: Window, cs: dict) -> list[dict]:
    # TODO: reuse check_featureflag.py — datafile pushes / experiment ramps in window.
    # Remember: FeatureFlag is both a change source AND a client-side conversion confounder.
    return []


def _terragrunt_applies(service_cfg: dict, window: Window, cs: dict) -> list[dict]:
    # TODO: GitHub Actions run history (terragrunt apply) touching service's project.
    return []
