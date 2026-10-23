"""gather_context — manifest-driven incident investigation (LangGraph node).

The whole point of this package: ONE generic implementation, N tenants, driven by
per-tenant YAML manifests in ../manifests/. Adding a tenant must require a new
manifest, never new code. If you find yourself hardcoding a service/query/log here,
push it into the manifest instead.
"""
