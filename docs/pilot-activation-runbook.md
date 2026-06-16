# VSA Pilot Activation Runbook

This runbook defines the path from the current governed scaffold to the final PHANTOM VSA pilot. It is intentionally gate-based: a later phase cannot be considered complete if an earlier validation target still fails.

## Phase 0: Local Scaffold Readiness

Estimated effort: same day after each implementation chunk.

Owner: engineering.

Goal: prove that the mock-backed workbench, audit, HITL, offline shell, and grounded summary path still work.

Required command:

```powershell
python scripts/pilot_readiness_report.py --target local --output-dir artifacts/readiness/local
python scripts/validate_api_contract.py --base-url http://localhost:8000 --output-dir artifacts/api-contract
python scripts/final_api_smoke.py --output-dir artifacts/final-api-smoke
python scripts/readiness_bundle.py --target local --output-dir artifacts/readiness/bundle-local
python scripts/local_handoff.py --target local --output-dir artifacts/local-handoff
```

Exit gate:

- Local readiness report passes.
- `/api/v1/integrations/readiness` reports no discovery or provider blockers for selected local/default providers.
- Backend tests, frontend build, Playwright smoke, eval harness, live-contract manifest check, and public-safety scan are green.
- API contract validation passes against the running backend, proving the browser is not pointed at a stale API process.
- Observability readiness passes; `OBSERVABILITY_PROVIDER=otlp_http` must include an approved OTLP endpoint.
- Readiness scaffold smoke passes for HITL sandbox submit, manager task status updates, and shelf-image analysis.
- Final API smoke passes for rep, manager, admin, HITL, audit, CRM draft, RGM, feedback, and metrics paths.
- Readiness MCP smoke passes for every local MCP server manifest.
- Readiness memory gate passes with the disabled default provider or a fully configured selected provider.
- Readiness bundle artifacts exist for handoff review.
- Readiness bundle includes runtime validation commands for the selected activation target.
- `SUMMARY_PROVIDER=template` is acceptable only for this phase.

## Phase 1: Real AI Demo Readiness

Estimated effort: 1-2 engineering days after approved model access is available.

Owner: delivery provisions approved model access; engineering validates configuration and eval artifacts.

Goal: prove the assistant is more than a deterministic template while retaining grounding, traceability, latency, and cost controls.

Required configuration:

```env
SUMMARY_PROVIDER=anthropic
ANTHROPIC_TOKEN_REF=<approved-token-reference>
ANTHROPIC_MODEL=claude-haiku-4-5
SUMMARY_FAIL_OPEN=false
```

Required command:

```powershell
python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai
python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval-ai --experiment-name phantom-vsa-evals --dry-run --output-dir artifacts/eval-ai
python scripts/ai_demo_eval_evidence.py --artifact-dir artifacts/eval-ai --output-dir artifacts/eval-ai
python scripts/pilot_readiness_report.py --target ai-demo --output-dir artifacts/readiness/ai-demo
```

Exit gate:

- Readiness report passes with `anthropic` present in eval providers.
- Hallucination rate remains `0.0`.
- Trace completeness remains `1.0`.
- Estimated cost stays below the configured `0.08 EUR` per interaction ceiling.
- P95 summary latency remains below `5000 ms`.
- `scripts/load_test.py` passes against the configured backend and writes load-test artifacts.
- AI-demo eval artifacts exist: `ai_demo_eval_evidence.json`, `ai_demo_eval_env.json`, and `ai_demo_eval.env.snippet`.
- When testing external identity, `LOAD_TEST_BEARER_TOKEN` is supplied from the approved runtime environment and is not written into artifacts.

## Phase 2: Live Data Contract Readiness

Estimated effort: 2-5 engineering days after platform access and view names are confirmed.

Owner: delivery owns client platform answers; engineering owns contract validation scripts and adapter configuration.

Goal: prove selected Databricks and Snowflake views match the corrected ontology before any pilot user sees live data.

Required configuration:

```env
OSA_ADAPTER=databricks
RGM_ADAPTER=databricks
STORE_MASTER_ADAPTER=snowflake
DISCOVERY_DATA_SHARING_MODEL=<approved-model>
DISCOVERY_DATA_RESIDENCY=<approved-region>
LIVE_DATA_CONTRACT_VALIDATED=true
```

Required command:

```powershell
python scripts/validate_live_data_contracts.py --output-dir artifacts/contracts/live
```

Exit gate:

- Required columns, non-null columns, normalized score columns, rep filters, territory filters, and alert business keys validate.
- Contract artifacts exist: `live_data_contract_report.json`, `live_data_contract_report.md`, and `readiness_env.json`.
- `LIVE_DATA_CONTRACT_LAST_VALIDATION_AT` and `LIVE_DATA_CONTRACT_VALIDATION_SUMMARY` are populated.
- `/api/v1/health/data-platform` reports `ready=true` for the selected Databricks/Snowflake adapters.
- No SQL string interpolation is introduced in live adapters.

## Phase 3: Identity And Governance Readiness

Estimated effort: 2-4 engineering days after SSO and audit target details are approved.

Owner: delivery owns SSO provider and audit target answers; engineering owns provider configuration and smoke tests.

Goal: move from mock identity and local audit to client-governed identity and auditable mirror.

Required configuration:

```env
AUTH_PROVIDER=external_jwt
EXTERNAL_JWT_ISSUER=<issuer>
EXTERNAL_JWT_AUDIENCE=<audience>
EXTERNAL_JWT_JWKS_URL=<jwks-url>
AUDIT_DUAL_WRITE_ENABLED=true
AUDIT_UNITY_CATALOG_TABLE=<approved-table>
```

Exit gate:

- Unauthorized store access still returns `404`.
- Mutating routes still ignore client-supplied rep identity.
- `/api/v1/health/auth` reports `ready=true` before `AUTH_PROVIDER=external_jwt` is used for pilot traffic.
- `/api/v1/health/audit-sink` reports `ready=true` before Unity Catalog audit primary or dual-write mode is used.
- `scripts/unity_audit_smoke.py` passes as a dry run before any credentialed audit mirror smoke is attempted.
- Audit mirror smoke test writes a parameterized row to the approved table.
- Guardrail classifier is either explicitly deferred or enabled with `GUARDRAIL_CLASSIFIER_BLOCK_THRESHOLD=0.85`; `/health/guardrails` must show the selected mode as ready, and `scripts/guardrail_classifier_smoke.py` must pass before credentialed classifier smoke.

## Phase 4: CRM, ERP, And HITL Write-Back

Estimated effort: 3-7 engineering days after sandbox endpoints and OAuth flow are confirmed.

Owner: delivery owns CRM/ERP sandbox readiness; engineering owns adapter smoke tests and rollback behavior.

Goal: preserve the existing HITL invariant while enabling real draft/write-back integrations.

Required configuration:

```env
CRM_ADAPTER=external
ERP_ADAPTER=external
DISCOVERY_CRM_PLATFORM=<approved-crm>
DISCOVERY_ERP_SANDBOX=<approved-sandbox>
```

Exit gate:

- Agents can draft but cannot submit.
- Approval payload hash must match at submit time.
- Rejected or modified drafts cannot be submitted.
- `/api/v1/health/action-providers` reports `ready=true` before external CRM or ERP providers are used.
- `scripts/action_provider_smoke.py` passes as a dry run before any credentialed CRM/ERP smoke is attempted.
- External write failures are audited and do not mutate draft approval history.

## Phase 5: Offline And Memory Expansion

Estimated effort: 3-6 engineering days after device and retention decisions are confirmed.

Owner: delivery owns device and retention policy answers; engineering owns offline and memory smoke tests.

Goal: make the pilot robust during store visits without creating uncontrolled local inference or persistent-memory risk.

Required configuration:

```env
MEMORY_PROVIDER=mem0
DISCOVERY_MEMORY_RETENTION_POLICY=<approved-retention>
DISCOVERY_MEMORY_SCOPES=<approved-scopes>
MEM0_TOKEN_REF=<approved-token-reference>
OFFLINE_AGENT_PROVIDER=none
OFFLINE_AGENT_ENABLED=false
OFFLINE_AGENT_KILL_SWITCH=true
```

Exit gate:

- Browser IndexedDB read cache works for route, store, alerts, and RGM data.
- Feedback sync remains idempotent with `{rep_id}:{client_event_uuid}`.
- Memory reads are scoped by rep/store and memory writes are non-blocking but telemetry-visible.
- `/api/v1/health/memory` reports `ready=true` for the selected memory provider before a pilot uses persistent memory.
- `scripts/memory_provider_smoke.py` passes as a dry run before any credentialed memory-provider smoke is attempted.
- Hermes/Ollama local inference remains behind a separate spike gate with device RAM, latency, tool-call accuracy criteria, and an explicit kill switch.

## Phase 5b: Shelf Image Provider Readiness

Estimated effort: 2-4 engineering days after device, image-retention, and data-residency decisions are confirmed.

Owner: delivery owns image capture policy and provider approval; engineering owns adapter smoke tests and audit grounding.

Goal: add image-assisted shelf review without allowing image-only replenishment decisions.

Required configuration:

```env
SHELF_IMAGE_ADAPTER=external
SHELF_IMAGE_ENDPOINT=<approved-provider-endpoint>
SHELF_IMAGE_TOKEN_REF=<approved-token-reference>
DISCOVERY_REP_DEVICE=<approved-device-runtime>
DISCOVERY_DATA_RESIDENCY=<approved-region>
```

Exit gate:

- External provider receives only approved image references plus grounded OOS alert context.
- `/api/v1/health/shelf-image` reports `ready=true` before external image analysis is used.
- Findings either reference supplied alert IDs or are labeled `unknown`/`low`.
- Every analysis emits `shelf_image_analysis_created` audit events.
- Image findings cannot create orders without the existing HITL draft and approval flow.

## Phase 6: Final VSA Pilot Gate

Estimated effort: 1-2 days after phases 1-5 are green.

Owner: engineering and delivery jointly sign off.

Required command:

```powershell
python scripts/pilot_readiness_report.py --target pilot --output-dir artifacts/readiness/pilot
python scripts/final_api_smoke.py --output-dir artifacts/final-api-smoke
python scripts/unity_audit_smoke.py --output-dir artifacts/unity-audit-smoke
python scripts/action_provider_smoke.py --output-dir artifacts/action-provider-smoke
python scripts/guardrail_classifier_smoke.py --output-dir artifacts/guardrail-classifier-smoke
python scripts/memory_provider_smoke.py --output-dir artifacts/memory-provider-smoke
python scripts/pilot_env_handoff.py --ai-demo-env artifacts/eval-ai/ai_demo_eval_env.json --live-data-env artifacts/contracts/live/readiness_env.json --output-dir artifacts/pilot-env
```

Final outcome:

- A field rep can authenticate through approved identity, review prioritized stores, inspect grounded OOS/RGM recommendations, run the AI assistant, submit feedback, create HITL-gated drafts, and work through brief offline periods.
- A manager can review territory performance and approval queues.
- A manager can assign auditable store tasks to reps, and reps can complete or block assigned work; full task workflow automation remains a later expansion.
- An admin can inspect filtered audit events and linked feedback.
- Every AI summary and write intent is grounded, audited, cost-tracked, and tied to the acting identity.
- `pilot_validation.env.snippet` contains only non-secret validation evidence keys and is reviewed before runtime configuration is updated.
