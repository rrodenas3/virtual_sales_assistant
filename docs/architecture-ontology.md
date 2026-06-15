# Virtual Sales Assistant Architecture And Ontology

This document is the public-safe architecture record for the MVP. It is derived from the internal architecture infographic and the implemented codebase, but intentionally omits client names, internal classifications, and proprietary brief labels.

## 1. Structural Accuracy Check

The internal architecture is organized into ten panels. The current repository implements a public-safe subset of those panels and documents what remains deferred.

| Panel | Architecture intent | Current repo status |
|---|---|---|
| Product vision | Field reps receive prioritized store actions before, during, and after visits | Implemented as a route/workbench UI with store priorities, OOS alerts, feedback, order drafts, and traceability |
| Competitive positioning | Differentiate through OSA, RGM, field execution, and governed action | Represented in product shape; no competitor names are included in public docs |
| 5-layer system architecture | Presentation, orchestration, MCP tools, data/AI platform, offline layer | Implemented: presentation, API/service orchestration, mock adapter ports, local MCP transport, offline feedback queue. Deferred: live data platform/Hermes |
| Agent mesh + memory + HITL | Supervisor routes to OSA/RGM/action agents, memory injection, approval gate, audit | Implemented: deterministic OSA/RGM services, feature-flagged graph-style OSA summary routing, memory port, HITL approvals, sandbox submit, audit. Deferred: production LangGraph/Mem0 |
| Data + governance | Data sources, guardrails, RBAC, immutable audit | Implemented: mock OSA/RGM sources, RBAC, guardrail stub, append-only audit tables. Deferred: real Snowflake/Databricks/Unity Catalog |
| Product UI surface | Rep, manager, admin, generative UI, trace/activity, offline banner | Implemented: rep workbench, manager summary, admin audit feed, trace drawer, offline queue status. Deferred: CopilotKit/AG-UI |
| 90-day roadmap | Phase 1 OSA, Phase 2 RGM/actions, Phase 3 offline/scale | Implemented through Phase 3 foundations in local/demo form |
| KPI framework | Day 30/60/90 adoption, precision, cost, traceability | Implemented: pilot metrics endpoint, feedback precision, summary cost telemetry, audit event counts, structured request telemetry |
| Technology decisions | FastAPI, React, PostgreSQL, MCP, LangGraph, Mem0, offline model | Implemented: FastAPI, React/Vite, SQLAlchemy/Alembic, adapter ports, local MCP transport. Deferred: production LangGraph/Mem0/FastMCP, offline model |
| Discovery and guardrails | Client discovery questions and scope exclusions | Implemented as docs/client-discovery.md, `/integrations/readiness`, and docs/spec-corrections.md |

## 2. System Architecture, Step By Step

### Step 1: Identity Boundary

The browser sends a mock JWT in local/demo mode. Backend auth is provider-based: `AUTH_PROVIDER=mock` is active for demo, and `AUTH_PROVIDER=external_jwt` validates issuer, audience, JWKS key ID, algorithm, role claim, and territory claim after SSO discovery gates are answered.

Claims:

```json
{
  "sub": "REP-001",
  "territory_code": "WEST-01",
  "role": "rep"
}
```

Roles:

- `rep`: can read assigned stores and submit feedback/drafts for assigned stores.
- `manager`: can read territory-level summaries and stores within the territory.
- `admin`: can read cross-rep audit data.

Backend rule: route handlers use authenticated identity from the token and do not trust client-supplied `rep_id`. The frontend also derives session IDs and offline idempotency keys from the active token claims.

### Step 2: Presentation Layer

Implemented in `frontend/src`.

Surfaces:

- Rep workbench: ranked stores, store detail, OOS alerts, RGM action band, draft/approval/sandbox-submit flow.
- Manager view: territory metrics, ranked store table, and approval queue.
- Admin view: filterable audit event feed and detail payload.
- Trace drawer: formula, source system, model version, freshness, and audit IDs.
- Offline status: browser queue count, online/offline status, PWA shell registration, and stale cache timestamp when IndexedDB read fallback is used.

### Step 3: API Layer

Implemented in `backend/backend/api/routes`.

Primary route groups:

- `/visits`: daily route priority.
- `/stores`: store detail, alerts, RGM recommendations.
- `/alerts`: feedback capture.
- `/orders`: draft creation, retrieval, sandbox submit.
- `/approvals`: approve/reject draft.
- `/crm`: visit-log drafts.
- `/sync`: idempotent offline feedback sync.
- `/integrations`: discovery readiness for live integration gates.
- `/metrics`: pilot KPI rollup.
- `/manager`: territory summary and approval queue.
- `/admin`: audit feed, filters, and detail.
- `/audit`: session-level trace lookup.
- `/agent`: grounded OSA summary.

### Step 4: Domain Services

Implemented in `backend/backend/services`.

Services:

- `rules.py`: deterministic priority reasons, alert recommendation, and confidence labels.
- `summary.py`: grounded summary generation from known alert IDs.
- `feedback.py`: single feedback creation path for online and offline sync.
- `audit.py`: append-only audit event writer and reader.
- `hashing.py`: stable payload hash for order draft approval safety.

### Step 5: Adapter Ports

Implemented in `backend/backend/adapters`.

Current adapter factory defaults:

- `MockOSAAdapter`: visit priority, OOS alerts, rep-scoped store details, territory summaries.
- `MockStoreMasterAdapter`: store-master detail port backed by the mock store seed data.
- `MockRGMAdapter`: promo, assortment, and upsell recommendations.
- `DatabricksOSAAdapter`, `DatabricksRGMAdapter`, and `SnowflakeStoreMasterAdapter`: parameterized query adapters behind discovery and credential gates.

REST and MCP must use the same adapter factory and service layer. Live data adapters build typed `QueryStatement` objects with named parameters; tests assert request values stay outside SQL text.

### Step 6: Persistence

Implemented with SQLAlchemy models and Alembic scaffold.

Tables:

- `sessions`
- `alert_feedback`
- `audit_events`
- `visit_logs`
- `order_drafts`
- `approval_records`
- `idempotency_records`

Local/test startup can auto-create tables for developer convenience. Production uses Alembic migrations and does not silently create tables.

### Step 6.5: Memory Boundary

Memory is behind `MemoryPort`. `MEMORY_PROVIDER=none` is the default and returns no memories. `MEMORY_PROVIDER=mem0` is discovery-gated until keys, retention policy, and memory scopes are confirmed. Summary audit payloads record memory provider and memory count, but grounded facts still come from OOS alerts.

### Step 7: Governance

Implemented in `backend/backend/governance` and the audit service boundary.

Controls:

- RBAC: reps are scoped to assigned stores; managers are scoped to territory; admins can read audit.
- Integration readiness blocks selected live providers until required discovery gates are answered.
- Unauthorized store access returns `404` for anti-enumeration.
- Summary guardrails use a provider boundary. Pattern blocking is active by default; external classifier mode is scaffolded with explicit fail-open/fail-closed behavior.
- Write-like flows are draft-first and require explicit approval before sandbox submit.
- Sandbox submit requires an approved draft and matching payload hash.
- Audit writes go through `AuditSink`; Postgres is active locally and Unity Catalog mirror dual-write is scaffolded behind discovery-gated settings.

### Step 8: Offline Sync

Implemented with frontend local storage for feedback queue, IndexedDB for read fallback, and backend idempotency records.

Flow:

1. Browser captures feedback.
2. If offline or request fails, event is queued in local storage.
3. On reconnect, queued events are posted to `/api/v1/sync/feedback-events`.
4. Backend enforces idempotency key format: `{rep_id}:{client_event_uuid}`.
5. Duplicate retries return the original feedback response.
6. Route, store, alert, and RGM reads write through to IndexedDB and can be shown with stale timestamps when online reads fail.

### Step 9: Metrics And Traceability

Implemented through audit events and `/api/v1/metrics/pilot`.

Tracked:

- Feedback count.
- Confirmed and false-positive counts.
- Alert precision proxy.
- Summary count.
- Estimated summary cost.
- Event counts by audit event type.
- HTTP request ID, status, path, and duration in structured telemetry logs.

### Step 10: Public Safety

The public repository intentionally excludes:

- Internal client/practice names.
- Internal classification labels.
- Local filesystem paths.
- Real API tokens, private keys, and credentials.
- Local SQLite database.
- Generated frontend build output.
- Dependency directories and Python caches.

The CI workflow includes `scripts/public_safety_scan.sh` to guard against accidental publication of sensitive markers.

## 3. Ontology

### Actors

| Entity | Meaning | Key properties |
|---|---|---|
| Rep | Field sales user assigned to stores | `rep_id`, `territory_code`, `role=rep` |
| Manager | Territory-level reviewer | `sub`, `territory_code`, `role=manager` |
| Admin | Governance/audit user | `sub`, `role=admin` |

### Commercial Objects

| Entity | Meaning | Key properties |
|---|---|---|
| Territory | Sales region containing stores and reps | `territory_code` |
| Store | Retail location assigned to a rep | `store_id`, `store_name`, `rep_id`, `territory_code`, `store_tier` |
| SKU | Sellable product unit | `sku_id`, `sku_name`, `category` |
| VisitPriority | Ranked store visit recommendation | `priority_score`, `rank`, `components`, `reasons` |
| OOSAlert | Shelf risk prediction | `alert_id`, `risk_score`, `root_cause_label`, `recommended_action`, `confidence_label` |
| RGMRecommendation | Revenue/category recommendation | promo, assortment gap, upsell opportunity |

### Action Objects

| Entity | Meaning | Key properties |
|---|---|---|
| AlertFeedback | Rep confirmation or dismissal of an alert | `feedback`, `notes`, `session_id` |
| OrderDraft | Draft replenishment order | `draft_id`, `payload_json`, `payload_hash`, `status` |
| ApprovalRecord | Human decision for an order draft | `approval_id`, `approved`, `draft_payload_hash` |
| VisitLog | Draft CRM visit record | `store_id`, `payload_json`, `status` |
| IdempotencyRecord | Offline duplicate protection | `idempotency_key`, `response_json` |
| AuditEvent | Append-only trace event | `event_id`, `event_type`, `resource_type`, `payload_json` |

### State Transitions

Order draft:

```text
DRAFT -> APPROVED -> SUBMITTED_SANDBOX
DRAFT -> REJECTED
REJECTED -> APPROVED
```

Feedback sync:

```text
captured_online -> persisted -> audited
captured_offline -> queued -> synced -> persisted -> audited
duplicate_sync -> original_response_returned
```

Alert lifecycle:

```text
generated_from_prediction -> displayed_to_rep -> feedback_recorded -> metrics_rollup
```

## 4. Accuracy Notes

The public repo is accurate to the revised hybrid architecture, not a literal implementation of every internal-spec technology choice.

Implemented now:

- FastAPI backend.
- React/Vite frontend.
- Mock JWT identity.
- RBAC.
- OSA/RGM mock adapter ports.
- Deterministic scoring and alert actions.
- HITL draft approval and sandbox submit.
- Offline feedback sync, IndexedDB read cache, and PWA app-shell/static asset cache.
- Manager approval queue and admin audit detail views.
- Audit and pilot metrics.
- Structured request telemetry and response timing headers.
- Local OSA eval harness.
- Alembic migration scaffold.
- Public-safety scan.
- Client discovery readiness endpoint and live-mode blockers.
- Config-gated Anthropic summary provider boundary with grounded identifier validation.
- Unity Catalog audit DDL artifact for future Delta mirror provisioning.

Deferred intentionally:

- Live Databricks/Snowflake credentials, view contracts, and production smoke tests.
- FastMCP dependency wiring. Mock-backed MCP tool functions use local JSON transport and share the backend adapter/service layer.
- Production LangGraph supervisor mesh. A deterministic graph-style scaffold is present behind a feature flag and can route OSA summaries.
- Active Mem0 memory by default. A null default and discovery-gated Mem0 HTTP contract are implemented.
- CopilotKit/AG-UI runtime. The client-pilot path uses the custom `/agent/run` SSE bridge first.
- MLflow/LangSmith/OpenTelemetry integrations beyond structured logs and local eval.
- Hermes/Ollama local inference.
- Real CRM/ERP write-back.
- Shelf-image recognition.

## 5. Next Architecture Steps

1. Validate external JWT settings against the selected client IdP after SSO discovery.
2. Run the summary eval path with `SUMMARY_PROVIDER=anthropic` before claiming AI-assistant pilot readiness.
3. Confirm Databricks/Snowflake view contracts and credentials, then run production smoke tests against live adapters.
4. Replace local JSON MCP transport with FastMCP dependency once runtime requirements are confirmed.
5. Replace the deterministic graph scaffold with production LangGraph only when multi-agent routing adds value beyond deterministic services.
6. Add MLflow evaluation once model/tool routing exists.
