# Tenant manifest schema

One file per tenant: `manifests/<tenant>.yaml`. The manifest is the contract that
makes investigation deterministic and tenant-agnostic. **Adding a tenant = a new file,
never new code.** If a primitive needs to know a service/query/log, it reads it here.

```yaml
tenant: <string>                 # matches the filename stem
region: <gcp-region>

observability:                   # where signals come from for this tenant
  metrics: { primary: gcp_monitoring|datadog, secondary: ... }
  logs: gcp_logging
  monitoring_project: <project>
  anomaly_monitors: datadog|none # if datadog, primitives prefer "is a monitor firing?"

edge:                            # optional — fronting gateway / VIP for attribution
  api_gateway: <name>
  legacy_vip: <host>

business_concerns:               # THE KEY SECTION: business signal -> technical subgraph
  <concern>:                     # e.g. conversions, payments_failing, search_degraded
    description: <string>
    funnel: [<service>, ...]     # ORDER MATTERS; fanned out for investigation
    kpis:
      - { metric: <name>, source: "<backend>:<query>" }

services:
  <service>:
    aliases: [<slo/runtime names>]   # optional; how it appears in SLOs/runtime
    runtime: gke|cloud-run|vm        # drives which change collector applies
    slis:
      latency_p95: { gcp_monitoring: "<filter>", datadog: "<query>" }   # str or {backend: query}
      error_rate:  { gcp_monitoring: "<filter>" }
    depends_on: [<service>, ...]     # optional; for blast-radius / ordering
    datastore: <datastore-key>       # optional; links to datastores:
    deploy_source: "argocd:<app>"    # for change correlation
    external_dep: <name>             # optional; third party (e.g. stripe)

datastores:
  <key>:
    type: cloudsql-mysql|cloudsql-postgres|mongodb-atlas|mariadb-vm|...
    instance|cluster|database: ...
    project: <project>
    slow_query: "<backend>:<query>"  # source for check_slow_queries; "NONE" if unavailable
    managed_by: <iac|spacewalk|...>  # optional governance note

change_sources:                  # feeds the highest-ROI primitive (change correlation)
  deploys:        { gke: ..., cloud_run: ..., legacy_vm: ... }
  feature_toggles:{ experiments: optimizely }
  config:         { iac: ..., legacy: ... }
```

## Source-string convention

SLI / KPI / slow_query `source` strings are passed **verbatim** to the primitive for
the named backend. Keep them queryable, not prose:

- `gcp_monitoring:` → a Monitoring filter / MQL (run via `fetch_timeseries`)
- `gcp_logging:`   → a Cloud Logging filter (run via `fetch_logs`, no severity filter)
- `datadog:`       → a Datadog metric/monitor query

## Validation of the abstraction

A second tenant (e.g. `tenant-b.yaml`) must run on the **same** `gather_context` code with
zero changes. If you can't add it with data alone, the schema is leaking — fix the
schema, not the agent.
