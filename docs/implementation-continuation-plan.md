# Continuation Implementation Plan

This plan continues the MVP from the current public repository state. It hardens production boundaries, keeps REST and MCP logic shared, and adds the remaining architecture scaffolds without introducing live client integrations before discovery is complete.

## Chunk Order

1. Plan artifact and repo hygiene.
2. Database lifecycle and Alembic CI.
3. Auth providers and frontend identity.
4. Adapter factory and integration boundaries.
5. MCP tool functions.
6. Manager approval queue and admin audit filters.
7. Evaluation harness.
8. Optional MCP transport.
9. LangGraph skeleton.
10. Memory scaffold.
11. Offline cache expansion.
12. PR hygiene.

## Per-Chunk Done Checklist

- New settings are documented in `.env.example`.
- Tests are added or updated without duplicating existing coverage.
- `docs/spec-compliance.md` is updated when spec posture changes.
- `bash ./scripts/public_safety_scan.sh` is green.
- The rep workbench smoke path is unchanged.
- No secrets, local user paths, client-confidential data, or internal screenshots are committed.
- Work is committed after each major chunk and never after more than five substantial implementation passes.

## Critical Implementation Rules

- REST routes and MCP tools must call the same adapter and service layer. Do not duplicate scoring, alert selection, approval, audit, or policy logic.
- The adapter factory must be implemented before MCP tool functions.
- Alembic must be the production database lifecycle. Startup table creation is local/test only.
- Frontend identity must come from the active demo token claims, not hardcoded `REP-001`.
- Manager approval queue extends existing manager capability without duplicating territory summary.
- LangGraph remains behind a feature flag until parity tests pass.
- Offline route, alert, store, and RGM cache should use IndexedDB; feedback idempotency remains tied to authenticated identity.

## Completed Continuation Additions

- Local MCP JSON transport and Compose wiring are implemented for OSA, store master, RGM, CRM, and orders.
- Structured request observability is implemented with request IDs, response timing, sampling controls, and `/health/observability`.
- Client discovery readiness gates are implemented before live SSO, data, CRM, ERP, and audit integrations.
- Store-master access is split behind a dedicated `StoreMasterPort`; OSA remains responsible for ranked territory and alert logic.
- `/agent/run` is scaffolded as a feature-flagged SSE bridge that reuses grounded OSA summary services.
- Frontend Playwright smoke coverage validates the mocked rep workbench route -> store -> alerts -> summary -> feedback flow.

## Deferred Spec Areas

- CopilotKit client package integration on top of the existing `/agent/run` SSE bridge.
- Unity Catalog audit dual-write beyond the `AuditSink` interface.
- OpenTelemetry, LangSmith, and MLflow production wiring.
- Haiku-based guardrail classifier.
- Live Databricks, Snowflake, CRM, ERP, SSO, and device integrations.
- Hermes/Ollama offline inference spike.
