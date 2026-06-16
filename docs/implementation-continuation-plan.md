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

## SDD Agent Gate

`AGENTS.md` and `CLAUDE.md` now exist at the repo root. Every new agent session (Codex
or Claude Code) reads these files before touching any source file. The gate encodes all
conventions, locked decisions, deferred technology, permanent spec corrections, public
safety rules, and the per-task done checklist. A thin redirect `AGENTS.md` also exists
one level above the repo root for agents launched from that directory.

Whenever a locked decision changes or a deferred technology is activated, update
`AGENTS.md` in the same commit as the code change.

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
- Eval artifacts now include MLflow-ready metrics/params plus an optional `scripts/log_eval_to_mlflow.py` handoff script.
- Shelf-image analysis now has a mock-first REST and MCP boundary with external-provider discovery gates; no real image pixels are analyzed by default.
- Manager-initiated work is scaffolded through auditable task assignment/status endpoints and a deployable `manager_tasks` migration.
- Local pilot readiness now includes scaffold smoke gates for HITL order submit, shelf-image analysis, and manager task transitions.
- Manager task MCP preview tools now share the backend task payload service with REST routes.
- AI-demo readiness is now exposed through `/health/ai` and `/integrations/readiness`, so template summaries cannot be confused with the required real-provider validation path.
- Live data contract validation now supports `--output-dir` artifacts, including a readiness env JSON for recording the validated status after credentialed checks.
- The frontend now exposes manager task assignment/cancel controls and rep task completion/block controls against the existing auditable task APIs.
- Unity Catalog audit mirroring now validates three-part table identifiers and has automated DDL drift coverage against the runtime insert contract.
- Summary endpoint load testing now supports configurable concurrency, p95 threshold failure, and JSON/Markdown artifacts.
- Local MCP transport now has a CI-backed manifest smoke script covering all seven MCP server modules and expected tool names.
- Pilot readiness reports now include the MCP manifest smoke result as a local scaffold gate.
- Offline local-agent inference now has a disabled-by-default governance scaffold with provider setting, kill switch, device RAM, latency, and tool-accuracy thresholds exposed through `/health/offline-agent`.
- External guardrail classifier mode now has `/health/guardrails` status and discovery gates for endpoint and data residency.
- Memory provider activation now has `/health/memory` status, showing whether Mem0 is enabled and which token, retention, or scope gates still block activation.
- External CRM/ERP write-back activation now has `/health/action-providers` status and a pilot-readiness gate for endpoint, token-reference, and discovery blockers.
- Live Databricks/Snowflake activation now has `/health/data-platform` status and a pilot-readiness gate for credentials, discovery answers, and live contract validation.
- External JWT activation now has `/health/auth` status and a pilot-readiness gate for SSO discovery, issuer, audience, and accepted algorithms.
- External shelf-image activation now has `/health/shelf-image` status and a pilot-readiness gate for endpoint, token-reference, device, and data-residency blockers.
- Unity Catalog audit activation now has `/health/audit-sink` status and a pilot-readiness gate for table identifier, Databricks credentials, discovery answers, and dual-write mode.
- OTLP observability activation now has a pilot-readiness gate through `/health/observability`, requiring endpoint and service-name configuration when `OBSERVABILITY_PROVIDER=otlp_http`.
- `/integrations/readiness` now aggregates provider readiness summaries and flattened provider blockers, so manager/admin users can see discovery gaps and selected-provider configuration gaps in one response.
- `scripts/readiness_bundle.py` now generates a local-safe handoff bundle with pilot readiness, MCP smoke, live-contract manifest, and manual checks for public safety, live credentials, and AI-demo validation.
- The manager command view now surfaces `/integrations/readiness` with selected live modes, provider blockers, and AI-demo posture.
- The admin governance view now surfaces `/integrations/readiness` beside audit events, so provider blockers, discovery blockers, and live-contract status are visible during trace review.
- `/integrations/readiness` now includes activation targets for local scaffold, AI demo, and final pilot readiness; manager/admin panels render those target states directly.
- Activation target blockers are calculated in a shared governance service and reused by the readiness report script, keeping API/UI state aligned with generated pilot artifacts.
- Manager/admin readiness panels and readiness bundle markdown now include activation blocker previews, so pilot owners can see the next blocking action without opening nested reports.
- Discovery gates now carry machine-readable owner metadata (`delivery`, `engineering`, or `shared`), and readiness reports group live-mode discovery blockers by owner.
- Readiness bundles now include the live-data readiness env-key manifest required to record credentialed contract validation results after approved runs.
- Databricks and Snowflake live-data access now have HTTP SQL API client contracts with token readiness gating and local payload/response tests; credentialed smoke remains discovery-gated.
- The Databricks bearer credential is intentionally omitted from public `.env.example`; it maps to the backend `databricks_token` setting through an approved secret channel.
- Snowflake store-master adapter construction now uses the same token gate as `/health/data-platform` and the Snowflake SQL client, avoiding late credential failures.
- Summary endpoint load testing now supports an approved runtime bearer-token override through `LOAD_TEST_BEARER_TOKEN` while keeping tokens out of reports.
- Pilot readiness reports, readiness bundles, `/integrations/readiness`, and manager/admin readiness panels now include target-specific runtime validation commands for local, AI-demo, and final pilot handoff from a shared governance helper.
- MLflow handoff now has a dry-run manifest mode that validates eval artifacts and writes `mlflow_handoff.json`/`mlflow_handoff.md` without requiring a managed MLflow server or local MLflow package.
- AI-demo readiness now requires explicit approved-provider eval evidence through `AI_DEMO_EVAL_VALIDATED`, with runtime commands, generated env snippets, and readiness bundle env keys documenting how to generate and record the proof.
- Final pilot validation now has a public-safe env handoff script that merges AI-demo and live-data validation evidence into `pilot_validation.env.snippet` without secrets.
- Final local API smoke now writes handoff artifacts for the complete rep-manager-admin workflow, including HITL submit, CRM draft, audit, metrics, and readiness paths.
- API contract validation now detects stale running backends that expose an old route set before frontend smoke or pilot handoff.
- Unity Catalog audit activation now has a dry-run smoke artifact that verifies the parameterized insert and DDL contract before any credentialed mirror write.
- CRM/ERP write-back activation now has a dry-run action provider smoke artifact that verifies outbound request shape, approval ID, and payload-hash binding without live endpoints.
- Guardrail classifier activation now has a dry-run smoke artifact covering below-threshold allow, threshold block, and fail-open pattern fallback behavior.
- Memory activation now has a dry-run smoke artifact covering default no-memory mode plus scoped Mem0 read/write payloads.
- Manager task APIs now support explicit status filtering, duplicate open assignment prevention, and the rep workbench requests only actionable open tasks while hiding terminal task history.
- API contract validation now checks required query parameter names for local FastAPI routes, including manager task status filters, instead of only checking path presence.
- Validation suite and readiness bundles now include target-specific activation evidence manifests, so local, AI-demo, and pilot handoffs list the required public-safe artifacts and env evidence keys in one place.
- Backend CI and agent verification instructions now lint the full `scripts/` directory instead of a brittle hand-maintained script list.
- `/integrations/readiness` and the manager/admin readiness panels now expose those activation evidence manifests, keeping UI, API, and CLI handoff requirements aligned.
- API contract validation now checks critical OpenAPI response fields for readiness and activation evidence schemas, not only route presence and query parameters.
- Final API smoke now validates readiness payload semantics, including local/AI-demo/pilot activation targets, runtime command sets, and pilot env handoff evidence.

## Deferred Spec Areas

- CopilotKit client package integration after the custom SSE pilot surface proves useful.
- Live Unity Catalog audit provisioning and credentialed smoke tests beyond the parameterized insert path and dry-run smoke artifact.
- LangSmith production wiring and a managed MLflow tracking server; local eval now emits MLflow-ready artifacts, dry-run handoff manifests, and optional logging.
- Production guardrail classifier endpoint selection and credentialed smoke tests beyond the local HTTP provider contract and dry-run classifier smoke.
- Mem0 workspace provisioning, retention approval, and credentialed smoke tests beyond the HTTP adapter contract, readiness endpoint, and dry-run memory smoke.
- Live Databricks, Snowflake, CRM, ERP, shelf-image, and device credentialed smoke tests after readiness gates pass; CRM/ERP now has a dry-run payload smoke first.
- Hermes/Ollama offline inference spike and offline local-agent tool calls.

## Locked Forward Decisions

- LLM library: official `anthropic` Python SDK.
- Pilot model setting: `ANTHROPIC_MODEL=claude-haiku-4-5`, configurable by environment.
- LangGraph: not a required dependency for Phase 1 (spec correction #9). Keep `AGENT_GRAPH_ENABLED=false`. Activate only after pilot data shows durable multi-turn graph state is needed.
- CopilotKit: permanently replaced by the custom `/agent/run` SSE bridge for Phase 1 (spec correction #10). Do not install `@copilotkit/*` packages unless the client explicitly requests generative UI components.
- Multi-agent mesh (Supervisor + Action Agent): Phase 2 scope. The deterministic rule engine handles routing for Phase 1. Single LLM call for OSA grounding is the agent layer for the pilot.
- Real AI gate: pilot validation must run the summary eval path once with `SUMMARY_PROVIDER=anthropic` and record `AI_DEMO_EVAL_VALIDATED=true`; template-only pilot mode is not sufficient for AI-assistant validation.
- Client discovery owner: delivery owns platform answers and approved secret provisioning; engineering owns readiness gates, validation scripts, and adapter code.
