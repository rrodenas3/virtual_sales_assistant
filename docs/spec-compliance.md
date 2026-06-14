# Spec And Plan Compliance Matrix

This document correlates the original internal MVP brief, the revised hybrid implementation plan, and the current local implementation.

## Current Implementation Status

| Area | Original spec intent | Revised plan decision | Current status |
|---|---|---|---|
| Product UX | Field assistant with before/during/after visit support | Workbench-first MVP, chat secondary | Implemented: route workbench, store detail, OOS alerts, RGM/action band, trace drawer |
| Auth / identity | SSO/CRM-mapped rep identity, unresolved in discovery | Mock JWT with `sub`, `territory_code`, `role`; ignore client rep IDs; scaffold external JWT | Implemented: provider boundary, mock JWT, fail-closed external JWT scaffold, rep/store RBAC, unauthorized store access returns `404` |
| Data layer | Snowflake/Databricks semantic views | Mock first; corrected schema contract; future adapters behind factory-selected ports | Implemented: mock adapters active; Databricks/Snowflake skeletons fail fast until credentials/contracts exist |
| Priority scoring | Formula sketched in OSA MCP SQL | Deterministic service formula with explainable components | Implemented and tested |
| OOS alerts | OOS risk + phantom inventory | Deterministic alert IDs, action rules, confidence labels | Implemented and tested |
| Agent orchestration | LangGraph multi-agent mesh | Phase 1 deterministic workflow; add graph later | Deferred intentionally; summary is grounded deterministic service |
| LLM grounding | Agent should not hallucinate SKU data | Summary constrained to supplied alert IDs | Implemented and tested |
| MCP layer | FastMCP servers for OSA/RGM/CRM/orders/store master | Top-level MCP placeholders; backend adapters own current logic | Partially scaffolded; MCP tool functions next, transport deferred |
| Memory | Mem0 rep/account/session memory | Not needed for read-only OSA pilot | Deferred intentionally |
| Governance | Guardrails, RBAC, policy, audit | Lightweight governance from Phase 1 | Implemented: RBAC, pattern guardrail, read-only policy stub, append-only audit behind `AuditSink` |
| HITL writes | Human approval before every write | Drafts and approvals only; sandbox submit requires approval/hash match | Implemented and tested |
| CRM | CRM read/write via MCP | Visit-log drafts only until CRM discovery completes | Implemented as draft-only local persistence |
| ERP/orders | ERP order submit with approval | Sandbox submit only, no real ERP side effects | Implemented and tested |
| Offline | Hermes/Ollama local inference + sync queue | Browser feedback queue first; Hermes spike later | Implemented: localStorage feedback queue + idempotent sync |
| Metrics/KPIs | Phase gates for precision, latency, hallucination, trace completeness, cost | Add pilot metrics endpoint and SQL docs | Implemented: `/metrics/pilot`, cost telemetry, docs |
| Frontend stack | React + Tailwind + CopilotKit/AG-UI | React/Vite workbench; no CopilotKit dependency for core workflow | Implemented; CopilotKit deferred intentionally |
| Manager view | Manager dashboard with territory overview | Add leadership summary before full dashboard | Implemented: `/manager/territory-summary` and manager UI mode |
| Admin console | Governance and audit console | Add audit feed before full admin console | Implemented: `/admin/audit-events` and admin UI mode |
| Migrations | Alembic migrations implied in repo structure | Add deployable migration scaffold and stop production auto-DDL | Implemented: Alembic `0001_initial`; startup auto-create is local/test only |
| Tests/eval | MLflow eval and agent tests | API/service tests first; MLflow later with real agent path | Implemented: 17 backend tests, frontend build verification |

## Implemented API Surface

```text
GET  /api/v1/health
GET  /api/v1/health/db
GET  /api/v1/metrics/pilot
GET  /api/v1/manager/territory-summary?territory_code=WEST-01
GET  /api/v1/admin/audit-events
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
GET  /api/v1/audit/session/{session_id}
```

## Intentional Deviations From Original Spec

These are not accidental gaps; they are deliberate corrections from the revised plan.

- No production LangGraph mesh yet. The original graph skeleton had invalid tool-result parsing and was too broad for Phase 1.
- No Mem0 yet. Account/rep memory comes after the OSA pilot proves useful.
- No real Snowflake/Databricks/MCP queries yet. Current mock adapters enforce the corrected data contract without live credentials.
- No CopilotKit dependency in the core UI. The MVP is an operational workbench first.
- No real ERP submit. `submit-sandbox` validates HITL policy and payload hash but has no external side effects.
- No Hermes/Ollama inference yet. Browser offline feedback sync is implemented first.
- No shelf image recognition, voice, digital shelf, manager-initiated tasks, or multi-tenant support.

## Remaining Work To Fully Meet The Original Spec

Highest priority:

1. Complete external JWT validation for Azure AD/Okta after issuer, audience, and JWK discovery details are known.
2. Implement parameterized Databricks/Snowflake query bodies behind the scaffolded adapters after view contracts are confirmed.
3. Replace MCP placeholders with real FastMCP servers once data-source credentials are known.
4. Expand manager/admin views into approval queue and richer audit console.
5. Add LangGraph only when multi-agent routing is needed for real RGM/action workflows.

Later:

- Mem0 memory scopes.
- MLflow evaluation harness.
- LangSmith or equivalent tracing.
- Hermes/Ollama offline agent spike.
- Shelf image MCP.
- Real CRM and ERP integrations after discovery gates are answered.

## Verification Commands

```powershell
cd backend
python -m ruff check backend tests
python -m pytest tests -q
alembic upgrade head

cd ../frontend
npm run build
```
