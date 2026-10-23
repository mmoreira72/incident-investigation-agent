# incident-agent

Multi-tenant, architecture-aware incident investigation agent (LangGraph). A vague
business signal — *"conversions dropped"* — is turned into a deterministic investigation
of *what deviates from normal in the last 6h–7d*, driven by a per-tenant **manifest**
rather than per-case scripts.

> One generic implementation, N tenants. **Adding a tenant = a new manifest, not new code.**

## Layout

| Path | What |
|------|------|
| `HANDOFF.md` | Start here — design, status, and the next task |
| `manifests/<tenant>.yaml` | The contract: business concern → technical subgraph, services, SLIs, datastores, change sources |
| `manifests/_schema.md` | Manifest schema |
| `manifests/GAPS-<tenant>.md` | What's missing / to validate |
| `gather_context/` | The generic node: manifest loader, 5 primitives, baseline, change correlation, LangGraph wiring |

## Quick start

```bash
pip install -r requirements.txt          # langgraph, pyyaml, gcp/datadog clients
python -m gather_context.graph           # compiles the gather_context sub-graph

# manifest-driven smoke test (no backends needed; stubs return not_implemented):
python - <<'PY'
from gather_context.manifest import load_manifest, funnel_for, service_cfg, change_sources
from gather_context.nodes import investigate_service, rank_and_correlate
m = load_manifest("acme")
w = {"start":"2026-05-30T00:00:00","end":"2026-05-30T06:00:00"}
an=[]
for s in funnel_for(m,"conversions"):
    an += investigate_service({"tenant":"acme","service_cfg":service_cfg(m,s),"window":w})["anomalies"]
print(rank_and_correlate({"anomalies":an})["hypothesis"])
PY
```

## Status

Scaffold runs end-to-end; primitives are stubs (`status="not_implemented"`). The
manifest is compiled from the Acme architecture survey and verified to drive the
flow (SLI queries come from the manifest, not code). Next: implement the primitives,
starting with change correlation. See `HANDOFF.md`.

## Source material (local)

- `docs/architecture-survey/` — the architecture deck + live monitoring export the manifest is compiled from.
- `~/Documents/personal/cloudengineerskills/` — the investigation skills + scripts the primitives reuse.
