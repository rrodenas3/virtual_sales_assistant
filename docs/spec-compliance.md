# Spec And Plan Compliance Matrix

This document correlates the original internal MVP brief, the revised hybrid implementation plan, and the current local implementation.

## Current Implementation Status

| Area | Original spec intent | Revised plan decision | Current status |
|---|---|---|---|
| Product UX | Field assistant with before/during/after visit support | Workbench-first MVP, chat secondary | Implemented: route workbench, store detail, OOS alerts, RGM/action band, trace drawer |
| Auth / identity | SSO/CRM-mapped rep identity, unresolved in discovery | Mock JWT with `sub`, `territory_code`, `role`; ignore client rep IDs; validate external JWT after discovery | Implemented: provider boundary, mock JWT, JWKS-backed external JWT validation, rep/store RBAC, unauthorized store access returns `404` |
| Data layer | Snowflake/Databricks semantic views | Mock first; corrected schema contract; future adapters behind factory-selected ports | Implemented: mock adapters active; Databricks/Snowflake parameterized query adapters scaffolded until credentials/contracts exist |
| Priority scoring | Formula sketched in OSA MCP SQL | Deterministic service formula with explainable components | Implemented and tested |
| OOS alerts | OOS risk + phantom inventory | Deterministic alert IDs, action rules, confidence labels | Implemented and tested |
| Agent orchestration | LangGraph multi-agent mesh | Phase 1 deterministic workflow; graph scaffold behind feature flag | Implemented: deterministic graph-style state/nodes; summary routes can use graph routing behind `AGENT_GRAPH_ENABLED` with parity tests |
| LLM grounding | Agent should not hallucinate SKU data | Summary constrained to supplied alert IDs | Implemented and tested |
| MCP layer | FastMCP servers for OSA/RGM/CRM/orders/store master | Top-level MCP functions share backend adapters/services; local JSON transport first | Implemented: mock-backed tool functions, local JSON transport, Compose services; FastMCP dependency deferred |
| Memory | Mem0 rep/account/session memory | Add provider scaffold; keep disabled for MVP | Implemented: `MemoryPort`, null adapter default, fail-closed Mem0 scaffold |
| Governance | Guardrails, RBAC, policy, audit | Lightweight governance from Phase 1 | Implemented: RBAC, guardrail provider boundary, read-only policy stub, append-only Postgres audit behind `AuditSink`, Unity Catalog mirror scaffold |
| Client discovery gates | Discovery before SSO/data/CRM/ERP integrations | Report and block live modes until required answers exist | Implemented: `/integrations/readiness` and live-mode gate checks |
| HITL writes | Human approval before every write | Drafts and approvals only; sandbox submit requires approval/hash match | Implemented and tested |
| CRM | CRM read/write via MCP | Visit-log drafts only until CRM discovery completes | Implemented as draft-only local persistence |
| ERP/orders | ERP order submit with approval | Sandbox submit only, no real ERP side effects | Implemented and tested |
| Offline | Hermes/Ollama local inference + sync queue | Browser feedback queue and IndexedDB read cache first; Hermes spike later | Implemented: localStorage feedback queue, idempotent sync, IndexedDB route/store/alert/RGM cache |
| Metrics/KPIs | Phase gates for precision, latency, hallucination, trace completeness, cost | Add pilot metrics endpoint and SQL docs | Implemented: `/metrics/pilot`, cost telemetry, docs |
| Observability | LangSmith/OpenTelemetry tracing | Structured logs first; vendor tracing later | Implemented: request IDs, response timing, structured HTTP events, observability health |
| Frontend stack | React + Tailwind + CopilotKit/AG-UI | React/Vite workbench; no CopilotKit dependency for core workflow | Implemented: workbench UI; feature-flagged `/agent/run` SSE scaffold; CopilotKit package integration deferred |
| Manager view | Manager dashboard with territory overview | Add leadership summary and approval queue before full dashboard | Implemented: `/manager/territory-summary`, `/manager/approval-queue`, and manager UI mode |
| Admin console | Governance and audit console | Add audit feed, filters, and detail before full admin console | Implemented: filtered `/admin/audit-events`, detail endpoint, and admin UI mode |
| Migrations | Alembic migrations implied in repo structure | Add deployable migration scaffold and stop production auto-DDL | Implemented: Alembic `0001_initial`; startup auto-create is local/test only |
| Tests/eval | MLflow eval and agent tests | API/service tests first; local eval harness before MLflow | Implemented: backend tests, visits -> store -> alerts -> feedback -> audit smoke path, Playwright workbench smoke, local OSA eval harness, frontend build verification |

## Implemented API Surface

```text
GET  /api/v1/health
GET  /api/v1/health/db
GET  /api/v1/health/observability
GET  /api/v1/integrations/readiness
GET  /api/v1/metrics/pilot
GET  /api/v1/manager/territory-summary?territory_code=WEST-01
GET  /api/v1/manager/approval-queue?territory_code=WEST-01
GET  /api/v1/admin/audit-events?event_type=&rep_id=&resource_type=&limit=&cursor=
GET  /api/v1/admin/audit-events/{event_id}
GET  /api/v1/visits/today?territory_code=WEST-01&date=YYYY-MM-DD
GET  /api/v1/stores/{store_id}
GET  /api/v1/stores/{store_id}/alerts
GET  /api/v1/stores/{store_id}/rgm-recommendations
POST /api/v1/alerts/{alert_id}/feedback
POST /api/v1/orders/drafts
GET  /api/v1/orders/drafts/{draft_id}
POST /api/v1/approvals/{draft_id}/approve
POST /api/v1/approvals/{draft_id}/reject
POST /api/v1/orders/drafts/{draft_id}/submit-sandbox
POST /api/v1/crm/visit-log-drafts
POST /api/v1/sync/feedback-events
POST /api/v1/agent/osa-summary
POST /api/v1/agent/run
GET  /api/v1/audit/session/{session_id}
```

## MCP Tool Function Mapping

| MCP tool function | Shared backend source | REST overlap |
|---|---|---|
| `mcp.osa.get_visit_priority` | OSA adapter factory | `GET /visits/today` |
| `mcp.osa.get_oos_alerts` | OSA adapter factory | `GET /stores/{id}/alerts` |
| `mcp.osa.get_phantom_inventory` | OSA adapter factory | Alert filter/badge |
| `mcp.store_master.get_store_health` | Store master adapter factory | `GET /stores/{id}` |
| `mcp.store_master.get_territory_stores` | OSA adapter factory for ranked territory summaries | `GET /manager/territory-summary` |
| `mcp.rgm.get_rgm_recommendations` | RGM and OSA adapter factories | `GET /stores/{id}/rgm-recommendations` |
| `mcp.orders.preview_order_draft_payload` | Stable payload hash service | `POST /orders/drafts` preflight |
| `mcp.crm.preview_visit_log_draft` | CRM draft payload contract | `POST /crm/visit-log-drafts` preflight |

## Intentional Deviations From Original Spec

These are not accidental gaps; they are deliberate corrections from the revised plan.

- No production LangGraph mesh yet. The graph-style scaffold exists behind a feature flag, and OSA summary routes can opt into graph routing with audited parity coverage.
- No active Mem0 memory yet. The memory port exists, but the default provider is `none`.
- No live Snowflake/Databricks/MCP credentials yet. Current mock adapters enforce the corrected data contract; live adapters build parameterized query statements and are ready for view-contract validation.
- No CopilotKit dependency in the core UI. The MVP is an operational workbench first; `/agent/run` is a feature-flagged SSE bridge for later AG-UI wiring.
- No real ERP submit. `submit-sandbox` validates HITL policy and payload hash but has no external side effects.
- No Hermes/Ollama inference yet. Browser offline feedback sync is implemented first.
- No shelf image recognition, voice, digital shelf, manager-initiated tasks, or multi-tenant support.

## Remaining Work To Fully Meet The Original Spec

Highest priority:

1. Validate Databricks/Snowflake query adapters against confirmed live view contracts and credentials.
2. Replace local JSON MCP transport with FastMCP dependency once runtime requirements and data-source credentials are known.
3. Replace the deterministic graph scaffold with production LangGraph only when multi-agent orchestration adds value beyond current services.
4. Wire live CRM/ERP submit after discovery gates are answered.

Later:

- CopilotKit client package integration on top of the feature-flagged `/agent/run` SSE bridge.
- Mem0 memory scopes, retention policy, and production provider wiring.
- MLflow integration beyond the local eval harness.
- Live Unity Catalog audit mirror implementation beyond the scaffolded dual-write sink.
- LangSmith/OpenTelemetry exporters beyond structured local telemetry.
- Live Haiku/Bedrock guardrail classifier implementation beyond the scaffold.
- Hermes/Ollama offline agent spike.
- Shelf image MCP.
- Real CRM and ERP integrations after discovery gates are answered.

## Verification Commands

```powershell
cd backend
python -m ruff check backend tests alembic ..\mcp ..\scripts\run_eval.py
python -m pytest tests -q
alembic upgrade head

cd ../frontend
npm run build

cd ..
python scripts/run_eval.py
bash ./scripts/public_safety_scan.sh
```
