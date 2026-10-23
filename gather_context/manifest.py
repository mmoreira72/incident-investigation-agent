"""Manifest loader. The manifest is the source of truth for WHAT to check and WHERE.
Nothing tenant-specific should live in code — only here.
"""
from __future__ import annotations
import os
import functools
import yaml

MANIFEST_DIR = os.environ.get(
    "MANIFEST_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "manifests")),
)


@functools.lru_cache(maxsize=None)
def load_manifest(tenant: str) -> dict:
    """Load and cache a tenant manifest. Raises if the tenant has no manifest —
    that's the contract: a tenant exists iff its manifest exists."""
    path = os.path.join(MANIFEST_DIR, f"{tenant}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No manifest for tenant '{tenant}' at {path}. "
            f"Add a manifest, not code."
        )
    with open(path) as f:
        return yaml.safe_load(f)


def funnel_for(manifest: dict, concern: str) -> list[str]:
    try:
        return manifest["business_concerns"][concern]["funnel"]
    except KeyError as e:
        raise KeyError(
            f"Concern '{concern}' not mapped for tenant '{manifest.get('tenant')}'. "
            f"Known: {list(manifest.get('business_concerns', {}))}"
        ) from e


def service_cfg(manifest: dict, name: str) -> dict:
    cfg = dict(manifest["services"][name])
    cfg["name"] = name
    # resolve datastore inline so the primitive doesn't reach back into the manifest
    ds = cfg.get("datastore")
    if ds:
        cfg["datastore_cfg"] = {**manifest.get("datastores", {}).get(ds, {}), "name": ds}
    return cfg


def kpis_for(manifest: dict, concern: str) -> list[dict]:
    return manifest["business_concerns"][concern].get("kpis", [])


def change_sources(manifest: dict) -> dict:
    return manifest.get("change_sources", {})


def observability(manifest: dict) -> dict:
    return manifest.get("observability", {})
