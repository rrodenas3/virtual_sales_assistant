# PHANTOM VSA

Phase 1 implementation of the PHANTOM Virtual Sales Assistant MVP.

This repo currently implements the secure OSA pilot slice:

- mock JWT identity
- external JWT validation scaffold with JWKS, issuer, audience, and claim mapping
- rep/store RBAC
- deterministic visit priority scoring
- deterministic OOS alert actions and confidence labels
- grounded OSA summaries
- feature-flagged custom agent run SSE bridge replacing CopilotKit for Phase 1
- append-only audit events
- alert feedback capture
- React workbench UI
- mock RGM recommendations
- order draft creation and approval records with payload-hash checks
- CRM visit-log drafts
- pilot metrics and spec compliance documentation
- local eval harness for OSA grounding, trace, auth, and latency checks
- Playwright workbench smoke test with mocked API responses
- structured request telemetry with request IDs and response timing
- feature-flagged graph-style agent scaffold with parity tests
- feature-flagged graph routing for grounded OSA summaries
- memory provider scaffold with null default and fail-closed Mem0 placeholder
- IndexedDB route, store, alert, and RGM cache for offline read fallback
- client discovery readiness gate for live integrations
- Alembic migration scaffold
- adapter factory for future Databricks/Snowflake integration
- parameterized Databricks/Snowflake query adapter scaffolds
- mock-backed MCP tool functions with local JSON transport
- manager territory summary
- manager task assignment and status transitions
- admin audit event feed
- integration readiness targets and activation evidence manifests
- shelf-image analysis boundary with mock default and external-provider readiness gates
- consolidated local handoff and validation-suite artifacts
- frontend demo role switcher for rep / manager / admin

See [docs/spec-compliance.md](docs/spec-compliance.md) for the current correlation between
the original MVP brief, the revised hybrid plan, and this implementation.
See [docs/architecture-ontology.md](docs/architecture-ontology.md) for the public-safe system
architecture, ontology, and step-by-step flow.

## Documentation Map

| Document | Use it for |
|---|---|
| [docs/spec-compliance.md](docs/spec-compliance.md) | Current spec posture, intentional deviations, remaining work |
| [docs/implementation-continuation-plan.md](docs/implementation-continuation-plan.md) | Chunk order, locked decisions, completed continuation work |
| [docs/spec-corrections.md](docs/spec-corrections.md) | Permanent corrections that override the original MVP brief |
| [docs/pilot-activation-runbook.md](docs/pilot-activation-runbook.md) | Local, AI-demo, and final pilot activation gates |
| [docs/architecture-ontology.md](docs/architecture-ontology.md) | Public-safe ontology, topology, architecture, and flow |
| [docs/infographic-5-unified-platform.md](docs/infographic-5-unified-platform.md) | Unified platform visual brief grounded in the implementation |
| [docs/pilot-metrics.md](docs/pilot-metrics.md) | KPI definitions, eval/load-test commands, and pilot metric queries |
| [docs/client-discovery.md](docs/client-discovery.md) | Delivery-owned client discovery questions before live integrations |

## Local Backend

```powershell
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Use this demo token for `REP-001`:

```text
Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9.
```

## Implemented API Surface

Phase 1:

```text
GET  /api/v1/health
GET  /api/v1/health/observability
GET  /api/v1/health/ai
GET  /api/v1/health/auth
GET  /api/v1/health/data-platform
GET  /api/v1/health/action-providers
GET  /api/v1/health/audit-sink
GET  /api/v1/health/guardrails
GET  /api/v1/health/memory
GET  /api/v1/health/offline-agent
GET  /api/v1/health/shelf-image
GET  /api/v1/integrations/readiness
GET  /api/v1/visits/today?territory_code=WEST-01&date=YYYY-MM-DD
GET  /api/v1/stores/{store_id}
GET  /api/v1/stores/{store_id}/alerts
GET  /api/v1/stores/{store_id}/rgm-recommendations
POST /api/v1/stores/{store_id}/shelf-image-analysis
POST /api/v1/alerts/{alert_id}/feedback
POST /api/v1/agent/osa-summary
POST /api/v1/agent/run
GET  /api/v1/audit/session/{session_id}
```

Phase 2 foundation:

```text
POST /api/v1/orders/drafts
GET  /api/v1/orders/drafts/{draft_id}
POST /api/v1/approvals/{draft_id}/approve
POST /api/v1/approvals/{draft_id}/reject
POST /api/v1/crm/visit-log-drafts
POST /api/v1/orders/drafts/{draft_id}/submit-sandbox
POST /api/v1/sync/feedback-events
GET  /api/v1/metrics/pilot
GET  /api/v1/manager/territory-summary?territory_code=WEST-01
GET  /api/v1/manager/approval-queue?territory_code=WEST-01
POST /api/v1/manager/tasks
GET  /api/v1/manager/tasks?territory_code=WEST-01&status=OPEN
GET  /api/v1/manager/my-tasks?status=OPEN
POST /api/v1/manager/tasks/{task_id}/status
GET  /api/v1/admin/audit-events?event_type=&rep_id=&resource_type=&limit=&cursor=
GET  /api/v1/admin/audit-events/{event_id}
```

Order drafts are still pilot artifacts. The sandbox submit endpoint enforces approval
and payload-hash matching, but does not call a real ERP. External CRM/ERP providers are
discovery-gated and default to local/sandbox behavior.

The frontend stores failed/offline feedback submissions in `localStorage` and syncs them through
`/api/v1/sync/feedback-events` when the browser returns online. Route, store, alert, and RGM read
payloads are cached in IndexedDB with visible stale timestamps when used.

## Local Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173/`. The Vite dev build unregisters stale service
workers by default so local PWA cache cannot blank the workbench. To test the
service worker in dev, set `VITE_ENABLE_SW_IN_DEV=true`; otherwise use
`npm run build && npm run preview`.

If Chrome still shows a blank page after switching branches, run a hard refresh
with `Ctrl + Shift + R`. If needed, clear site data for `localhost:5173` in
DevTools under Application -> Storage.

To verify the full local loop once both services are running:

```powershell
python scripts/local_dev_smoke.py --output-dir artifacts/local-dev-smoke
```

To generate one consolidated local validation bundle:

```powershell
python scripts/validation_suite.py --target local --include-local-dev-smoke --output-dir artifacts/validation-suite
```

To verify locked architecture decisions stay aligned with the spec corrections:

```powershell
python scripts/spec_decision_guard.py --output-dir artifacts/spec-decision-guard
```

## Local MCP Transports

The `mcp/` servers expose a lightweight local JSON transport around the same backend adapter/service layer used by REST.

```powershell
python -m mcp.osa.server --list
python -m mcp.osa.server --call get_visit_priority --args-json '{"rep_id":"REP-001","territory_code":"WEST-01","visit_date":"2026-06-14"}'
```

`docker-compose.yml` includes one local MCP service per domain: OSA, store master,
RGM, orders, CRM, shelf image, and manager tasks.

## CI

The public repository runs GitHub Actions for:

- backend lint and tests
- local OSA eval harness
- Alembic migration smoke test
- frontend production build
- public-safety scan for accidental internal names, local paths, and obvious secret markers

Run the local eval harness directly with:

```powershell
python scripts/run_eval.py
```
