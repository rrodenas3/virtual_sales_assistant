# Spec And Plan Compliance Matrix

This document correlates the original internal MVP brief, the revised hybrid implementation plan, and the current local implementation.

## Current Implementation Status

| Area | Original spec intent | Revised plan decision | Current status |
|---|---|---|---|
| Product UX | Field assistant with before/during/after visit support | Workbench-first MVP, chat secondary | Implemented: route workbench, store detail, OOS alerts, RGM/action band, trace drawer |
| Auth / identity | SSO/CRM-mapped rep identity, unresolved in discovery | Mock JWT with `sub`, `territory_code`, `role`; ignore client rep IDs; validate external JWT after discovery | Implemented: provider boundary, mock JWT, JWKS-backed external JWT validation, auth readiness, rep/store RBAC, unauthorized store access returns `404` |
| Data layer | Snowflake/Databricks semantic views | Mock first; corrected schema contract; future adapters behind factory-selected ports | Implemented: mock adapters active; Databricks/Snowflake parameterized query adapters scaffolded; Snowflake SQL API client contract, live contract manifest, validation script, readiness env manifest, and data-platform readiness added for credentialed environments |
| Priority scoring | Formula sketched in OSA MCP SQL | Deterministic service formula with explainable components | Implemented and tested |
| OOS alerts | OOS risk + phantom inventory | Deterministic alert IDs, action rules, confidence labels | Implemented and tested |
| Agent orchestration | LangGraph multi-agent mesh | Phase 1 deterministic workflow; graph scaffold behind feature flag | Implemented: deterministic graph-style state/nodes; summary routes can use graph routing behind `AGENT_GRAPH_ENABLED` with parity tests |
| LLM grounding | Agent should not hallucinate SKU data | Summary constrained to supplied alert IDs; Anthropic SDK provider is config-gated behind deterministic template fallback | Implemented: `SUMMARY_PROVIDER=template|anthropic`, grounded identifier validation, provider metadata in audit |
| MCP layer | FastMCP servers for OSA/RGM/CRM/orders/store master | Top-level MCP functions share backend adapters/services; local JSON transport first | Implemented: mock-backed tool functions, local JSON transport, Compose services, and CI-backed manifest smoke; FastMCP dependency deferred |
| Memory | Mem0 rep/account/session memory | Add provider scaffold; keep disabled for MVP | Implemented: `MemoryPort`, null adapter default, discovery-gated Mem0 HTTP contract, summary audit metadata, `/health/memory` readiness, and dry-run scoped memory smoke |
| Governance | Guardrails, RBAC, policy, audit | Lightweight governance from Phase 1 | Implemented: RBAC, guardrail provider boundary, guardrail health/readiness gates, read-only policy stub, append-only Postgres audit behind `AuditSink`, audit-sink readiness, parameterized Unity Catalog audit insert path, identifier validation, DDL drift tests, dry-run Unity audit smoke artifacts, and dry-run guardrail classifier smoke |
| Client discovery gates | Discovery before SSO/data/CRM/ERP integrations | Report and block live modes until required answers exist | Implemented: `/integrations/readiness`, live-mode gate checks, provider readiness aggregation, local/AI-demo/pilot activation target blockers in UI and handoff artifacts, target runtime command manifest in API/UI/artifacts, machine-readable owner model, AI-demo eval evidence status, live data contract validation status fields, and public-safe pilot env handoff |
| HITL writes | Human approval before every write | Drafts and approvals only; sandbox submit requires approval/hash match | Implemented and tested |
| CRM | CRM read/write via MCP | Visit-log drafts only until CRM discovery completes | Implemented: local draft provider default plus discovery-gated external CRM HTTP adapter, action-provider readiness, and dry-run outbound payload smoke |
| ERP/orders | ERP order submit with approval | Sandbox submit only, no real ERP side effects by default | Implemented: sandbox provider default plus discovery-gated external ERP HTTP adapter, action-provider readiness, and dry-run approval/hash payload smoke |
| Offline | Hermes/Ollama local inference + sync queue | Browser feedback queue, IndexedDB read cache, and PWA shell first; Hermes spike later | Implemented: localStorage feedback queue, idempotent sync, IndexedDB route/store/alert/RGM cache, manifest, service worker app shell/static cache, and disabled-by-default offline-agent kill-switch scaffold |
| Shelf image | Image-based shelf recognition MCP | Mock-first image-analysis boundary; external provider only after device/data-residency discovery | Implemented: `POST /stores/{id}/shelf-image-analysis`, `mcp.shelf_image.analyze_shelf_image`, mock grounded findings from OOS alerts, external HTTP adapter scaffold, and shelf-image readiness |
| Metrics/KPIs | Phase gates for precision, latency, hallucination, trace completeness, cost | Add pilot metrics endpoint and SQL docs | Implemented: `/metrics/pilot`, cost telemetry, docs, eval artifacts, and thresholded summary endpoint load-test artifacts |
| Observability | LangSmith/OpenTelemetry tracing | Structured logs first; vendor tracing later | Implemented: request IDs, response timing, structured HTTP events, OTLP HTTP log export boundary, observability health/readiness, audit mirror failure telemetry |
| Frontend stack | React + Tailwind + CopilotKit/AG-UI | React/Vite workbench; no CopilotKit dependency for core workflow | Implemented: workbench UI; custom feature-flagged `/agent/run` SSE assistant panel; CopilotKit package integration deferred |
| Manager view | Manager dashboard with territory overview and manager-initiated work | Add leadership summary, approval queue, readiness, and auditable task workflow before full dashboard | Implemented: `/manager/territory-summary`, `/manager/approval-queue`, `/integrations/readiness`, `/manager/tasks`, `/manager/my-tasks`, `/manager/tasks/{id}/status`, task status filtering, duplicate-open assignment prevention, manager readiness panel, task assignment/cancel, and rep task completion/block controls |
| Admin console | Governance and audit console | Add audit feed, filters, readiness, and detail before full admin console | Implemented: filtered `/admin/audit-events`, detail endpoint, admin UI mode, and governance readiness panel |
| Migrations | Alembic migrations implied in repo structure | Add deployable migration scaffold and stop production auto-DDL | Implemented: Alembic `0001_initial`; startup auto-create is local/test only |
| Tests/eval | MLflow eval and agent tests | API/service tests first; local eval harness before managed MLflow | Implemented: backend tests, visits -> store -> alerts -> feedback -> audit smoke path, API contract validation, final API smoke handoff, Playwright workbench smoke, local OSA eval harness with optional required-provider gate, MLflow-ready artifact export, dry-run MLflow handoff manifest, generated AI-demo eval evidence env snippet, public-safe pilot validation env handoff, explicit AI-demo eval evidence gate, pilot readiness report with shared activation target blockers, readiness bundle, frontend build verification, summary provider unit coverage |

## Implemented API Surface

```text
GET  /api/v1/health
GET  /api/v1/health/db
GET  /api/v1/health/observability
GET  /api/v1/health/ai
GET  /api/v1/health/offline-agent
GET  /api/v1/health/guardrails
GET  /api/v1/health/memory
GET  /api/v1/health/action-providers
GET  /api/v1/health/data-platform
GET  /api/v1/health/auth
GET  /api/v1/health/shelf-image
GET  /api/v1/health/audit-sink
GET  /api/v1/integrations/readiness
GET  /api/v1/metrics/pilot
GET  /api/v1/manager/territory-summary?territory_code=WEST-01
GET  /api/v1/manager/approval-queue?territory_code=WEST-01
POST /api/v1/manager/tasks
GET  /api/v1/manager/tasks?territory_code=WEST-01&status=OPEN
GET  /api/v1/manager/my-tasks?status=OPEN
POST /api/v1/manager/tasks/{task_id}/status
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
POST /api/v1/stores/{store_id}/shelf-image-analysis
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
| `mcp.shelf_image.analyze_shelf_image` | Shelf image adapter factory + OSA adapter grounding | `POST /stores/{id}/shelf-image-analysis` |
| `mcp.manager.preview_manager_task_payload` | Manager task payload service | `POST /manager/tasks` preflight |
| `mcp.manager.preview_manager_task_status_update` | Manager task payload service | `POST /manager/tasks/{id}/status` preflight |

## Intentional Deviations From Original Spec

These are not accidental gaps; they are deliberate corrections from the revised plan.

- No production LangGraph mesh yet. The graph-style scaffold exists behind a feature flag, and OSA summary routes can opt into graph routing with audited parity coverage. The client-pilot path explicitly defers adding LangGraph dependencies until multi-agent routing adds value beyond current services.
- No active Mem0 memory by default. The memory port exists, `none` is the default provider, and Mem0 is discovery-gated behind token-reference, retention, and scope settings visible through `/health/memory`; dry-run memory smoke validates scoped request shape before credentialed activation.
- No live Snowflake/Databricks/MCP credentials yet. Current mock adapters enforce the corrected data contract; live adapters build parameterized query statements, Databricks and Snowflake HTTP clients have local payload contracts, `scripts/validate_live_data_contracts.py` is ready for view-contract validation in a credentialed environment, and `/health/data-platform` exposes selected live-data blockers.
- No CopilotKit dependency in the core UI. The client-pilot path now uses the custom `/agent/run` SSE assistant panel first and defers CopilotKit package integration.
- Anthropic summary generation is implemented as a config-gated provider boundary. `template` remains the default, but `/health/ai`, `/integrations/readiness`, AI-demo eval evidence fields, and final AI-assistant pilot validation make template-only mode visibly not AI-demo-ready.
- External guardrail classifier behavior is implemented against an HTTP contract with `GUARDRAIL_CLASSIFIER_BLOCK_THRESHOLD=0.85`; production endpoint selection remains discovery/configuration work and is now visible through `/health/guardrails`, with a dry-run classifier smoke available before credentialed validation.
- No real ERP submit by default. `submit-sandbox` validates HITL policy and payload hash; external CRM/ERP providers are discovery-gated, disabled unless configured, and visible through `/health/action-providers`.
- No Hermes/Ollama inference yet. Browser offline feedback sync, IndexedDB read fallback, PWA app-shell caching, and a disabled-by-default offline-agent governance scaffold are implemented first.
- No production shelf image recognition, voice, digital shelf execution, or multi-tenant support. Shelf-image analysis is currently a governed mock/external-provider boundary with `/health/shelf-image` readiness. Manager-initiated tasks support auditable assignment plus completion/block/cancel transitions, not a full workflow engine.

## Remaining Work To Fully Meet The Original Spec

Highest priority:

1. Run `scripts/validate_live_data_contracts.py` against confirmed live view contracts and credentials, then record validation status in readiness settings.
2. Run `scripts/pilot_readiness_report.py --target ai-demo` with `SUMMARY_PROVIDER=anthropic` before calling the product an AI assistant.
3. Replace local JSON MCP transport with FastMCP dependency once runtime requirements and data-source credentials are known.
4. Replace the deterministic graph scaffold with production LangGraph only when multi-agent orchestration adds value beyond current services.
5. Wire live CRM/ERP submit after discovery gates are answered.

Later:

- CopilotKit remains a later optional UI dependency after the custom SSE assistant panel.
- Mem0 workspace provisioning, retention approval, and credentialed smoke tests.
- Managed MLflow tracking server configuration beyond local MLflow-ready artifact export.
- Credentialed Unity Catalog audit smoke tests beyond the parameterized insert path.
- LangSmith exporters and production collector wiring beyond the OTLP HTTP log boundary.
- Live Haiku/Bedrock guardrail classifier implementation beyond the scaffold.
- Hermes/Ollama offline agent spike and local tool-call accuracy testing.
- Credentialed shelf-image provider smoke tests after image policy and data residency gates are answered.
- Credentialed CRM and ERP smoke tests after discovery gates are answered.

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
python scripts/pilot_readiness_report.py --target local
python scripts/readiness_bundle.py --target local --output-dir artifacts/readiness/bundle-local
python scripts/validate_live_data_contracts.py --manifest-only
python scripts/mcp_smoke.py
bash ./scripts/public_safety_scan.sh
```

For AI-demo or pilot validation, run `python scripts/run_eval.py --require-provider anthropic` after configuring `SUMMARY_PROVIDER=anthropic`.
