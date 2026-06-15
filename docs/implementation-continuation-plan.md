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
- Audit sinks support discovery-gated Postgres-primary dual-write scaffolding for a future Unity Catalog mirror.
- External JWT validation is implemented behind discovery gates with JWKS, issuer, audience, algorithm, role-claim, and territory-claim checks.
- Guardrails support a provider boundary: default pattern checks plus fail-open/fail-closed external classifier scaffolding.
- Databricks and Snowflake adapters build parameterized `QueryStatement` objects with injectable SQL clients and schema mappers.
- OSA summary routes can use the graph scaffold behind `AGENT_GRAPH_ENABLED`; audit payloads record `orchestration_mode`.
- Live adapter row mapping is shared by helper functions; Snowflake no longer calls Databricks adapter methods by duck typing.
- OSA summary generation has a provider boundary: `SUMMARY_PROVIDER=template|anthropic`. The official Anthropic SDK is the selected LLM client; production LangGraph and CopilotKit remain deferred for the client-pilot path.
- Live data contract validation is scaffolded through `scripts/validate_live_data_contracts.py`, backend column manifests, row-level normalization checks, and readiness fields for validation status.
- Governance controls now include a parameterized Unity Catalog audit insert path behind `AuditSink` and an HTTP external-classifier guardrail provider with the configured `0.85` block threshold.
- The rep workbench includes a feature-flagged custom SSE assistant panel backed by `POST /agent/run`; CopilotKit remains deferred.
- Offline/PWA hardening now includes installability metadata, an app-shell service worker, static asset caching, and E2E registration coverage. API read fallback remains handled by IndexedDB in the app; writes are never service-worker cached.
- CRM and ERP action boundaries now use provider-selected ports: local CRM drafts and sandbox ERP remain defaults, while external HTTP providers are discovery-gated.
- Memory now has discovery-gated Mem0 HTTP read/write contracts, scoped metadata, and summary audit fields. `MEMORY_PROVIDER=none` remains the default.
- Pilot activation gates now distinguish local scaffold readiness, AI demo readiness, and final pilot readiness through `scripts/pilot_readiness_report.py` and `docs/pilot-activation-runbook.md`.
- Observability now has an OTLP HTTP export boundary behind `OBSERVABILITY_PROVIDER=otlp_http`, while structured local logging remains the default.

## Deferred Spec Areas

- CopilotKit client package integration after the custom SSE pilot surface proves useful.
- Live Unity Catalog audit provisioning and credentialed smoke tests beyond the parameterized insert path.
- LangSmith and MLflow production wiring; OpenTelemetry is scaffolded through an OTLP HTTP log exporter but not connected to a production collector by default.
- Production guardrail classifier endpoint selection and credentialed smoke tests beyond the local HTTP provider contract.
- Mem0 workspace provisioning, retention approval, and credentialed smoke tests beyond the HTTP adapter contract.
- Live Databricks, Snowflake, CRM, ERP, and device integrations.
- Hermes/Ollama offline inference spike and offline local-agent tool calls.

## Locked Forward Decisions

- LLM library: official `anthropic` Python SDK.
- Pilot model setting: `ANTHROPIC_MODEL=claude-haiku-4-5`, configurable by environment.
- LangGraph: defer production dependency; keep current graph-style scaffold as a parity/migration harness.
- CopilotKit: defer for pilot; use the existing custom `/agent/run` SSE bridge first.
- Real AI gate: pilot validation must run the summary eval path once with `SUMMARY_PROVIDER=anthropic`; template-only pilot mode is not sufficient for AI-assistant validation.
- Client discovery owner: delivery owns platform answers and approved secret provisioning; engineering owns readiness gates, validation scripts, and adapter code.
