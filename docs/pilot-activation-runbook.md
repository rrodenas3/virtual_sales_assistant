# VSA Pilot Activation Runbook

This runbook defines the path from the current governed scaffold to the final PHANTOM VSA pilot. It is intentionally gate-based: a later phase cannot be considered complete if an earlier validation target still fails.

## Phase 0: Local Scaffold Readiness

Estimated effort: same day after each implementation chunk.

Owner: engineering.

Goal: prove that the mock-backed workbench, audit, HITL, offline shell, and grounded summary path still work.

Required command:

```powershell
python scripts/pilot_readiness_report.py --target local --output-dir artifacts/readiness/local
```

Exit gate:

- Local readiness report passes.
- Backend tests, frontend build, Playwright smoke, eval harness, live-contract manifest check, and public-safety scan are green.
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
python scripts/pilot_readiness_report.py --target ai-demo --output-dir artifacts/readiness/ai-demo
```

Exit gate:

- Readiness report passes with `anthropic` present in eval providers.
- Hallucination rate remains `0.0`.
- Trace completeness remains `1.0`.
- Estimated cost stays below the configured `0.08 EUR` per interaction ceiling.
- P95 summary latency remains below `5000 ms`.

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
- `LIVE_DATA_CONTRACT_LAST_VALIDATION_AT` and `LIVE_DATA_CONTRACT_VALIDATION_SUMMARY` are populated.
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
- Audit mirror smoke test writes a parameterized row to the approved table.
- Guardrail classifier is either explicitly deferred or enabled with `GUARDRAIL_CLASSIFIER_BLOCK_THRESHOLD=0.85`.

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
```

Exit gate:

- Browser IndexedDB read cache works for route, store, alerts, and RGM data.
- Feedback sync remains idempotent with `{rep_id}:{client_event_uuid}`.
- Memory reads are scoped by rep/store and memory writes are non-blocking but telemetry-visible.
- Hermes/Ollama local inference remains behind a separate spike gate with device RAM, latency, and tool-call accuracy criteria.

## Phase 6: Final VSA Pilot Gate

Estimated effort: 1-2 days after phases 1-5 are green.

Owner: engineering and delivery jointly sign off.

Required command:

```powershell
python scripts/pilot_readiness_report.py --target pilot --output-dir artifacts/readiness/pilot
```

Final outcome:

- A field rep can authenticate through approved identity, review prioritized stores, inspect grounded OOS/RGM recommendations, run the AI assistant, submit feedback, create HITL-gated drafts, and work through brief offline periods.
- A manager can review territory performance and approval queues.
- An admin can inspect filtered audit events and linked feedback.
- Every AI summary and write intent is grounded, audited, cost-tracked, and tied to the acting identity.
