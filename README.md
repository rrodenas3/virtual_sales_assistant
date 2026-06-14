# PHANTOM VSA

Phase 1 implementation of the PHANTOM Virtual Sales Assistant MVP.

This repo currently implements the secure OSA pilot slice:

- mock JWT identity
- rep/store RBAC
- deterministic visit priority scoring
- deterministic OOS alert actions and confidence labels
- grounded OSA summaries
- append-only audit events
- alert feedback capture
- React workbench UI
- mock RGM recommendations
- order draft creation and approval records with payload-hash checks
- CRM visit-log drafts
- pilot metrics and spec compliance documentation
- Alembic migration scaffold
- adapter factory for future Databricks/Snowflake integration
- mock-backed MCP tool functions with transport deferred
- manager territory summary
- admin audit event feed
- frontend demo role switcher for rep / manager / admin

See [docs/spec-compliance.md](docs/spec-compliance.md) for the current correlation between
the original MVP brief, the revised hybrid plan, and this implementation.
See [docs/architecture-ontology.md](docs/architecture-ontology.md) for the public-safe system
architecture, ontology, and step-by-step flow.

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
GET  /api/v1/visits/today?territory_code=WEST-01&date=YYYY-MM-DD
GET  /api/v1/stores/{store_id}
GET  /api/v1/stores/{store_id}/alerts
POST /api/v1/alerts/{alert_id}/feedback
POST /api/v1/agent/osa-summary
GET  /api/v1/audit/session/{session_id}
```

Phase 2 foundation:

```text
GET  /api/v1/stores/{store_id}/rgm-recommendations
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
GET  /api/v1/admin/audit-events?event_type=&rep_id=&resource_type=&limit=&cursor=
GET  /api/v1/admin/audit-events/{event_id}
```

Order drafts are still pilot artifacts. There is no ERP submission endpoint yet.
The sandbox submit endpoint enforces approval and payload-hash matching, but does not call a real ERP.

The frontend stores failed/offline feedback submissions in `localStorage` and syncs them through
`/api/v1/sync/feedback-events` when the browser returns online.

## Local Frontend

```powershell
cd frontend
npm install
npm run dev
```

## CI

The public repository runs GitHub Actions for:

- backend lint and tests
- Alembic migration smoke test
- frontend production build
- public-safety scan for accidental internal names, local paths, and obvious secret markers
