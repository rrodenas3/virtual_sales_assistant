# AGENTS.md — PHANTOM VSA

PHANTOM is a governed, multi-agent field sales assistant for CPG field representatives.
This repo (`phantom/`) is the implementation layer.

The authoritative MVP specification is an **internal document that lives outside this
repo and must never be committed here.** All implementation decisions are derived from
that spec and recorded in the docs listed below.

---

## Read These Before Implementing Anything

| Document | Purpose |
|---|---|
| `docs/spec-compliance.md` | Current implementation state vs. spec; intentional deviations; remaining work |
| `docs/implementation-continuation-plan.md` | Chunk order, critical rules, locked decisions, completed additions |
| `docs/spec-corrections.md` | Permanent overrides to the original spec — these win over the spec text |
| `docs/pilot-activation-runbook.md` | How readiness gates work and what blocks each activation target |
| `docs/architecture-ontology.md` | Public-safe architecture, ontology, topology, and step-by-step flow |
| `docs/infographic-5-unified-platform.md` | Public-safe unified platform visual brief grounded in implementation details |

If a spec area you are about to implement is not the next chunk in
`implementation-continuation-plan.md`, stop and confirm before proceeding.

---

## Actual Repo Layout

The layout below reflects what exists. It differs from the spec's proposed layout.
Do not create directories or files that mirror the spec layout unless a plan chunk
explicitly calls for it.

```
phantom/
├── AGENTS.md                            ← you are here
├── CLAUDE.md                            ← thin Claude Code pointer to this file
├── README.md
├── .env.example                         ← every feature flag and env var with safe defaults
├── docker-compose.yml
├── .github/workflows/ci.yml             ← three jobs: backend, frontend, public-safety
│
├── backend/
│   ├── pyproject.toml                   ← Python 3.11+, deps, ruff + pytest config
│   ├── alembic.ini
│   ├── alembic/versions/                ← 0001_initial, 0002_manager_tasks
│   └── backend/
│       ├── main.py                      ← FastAPI app, routers, middleware, lifespan
│       ├── config.py                    ← all Settings (pydantic-settings, reads .env)
│       ├── deps.py                      ← FastAPI dependency injection
│       ├── adapters/                    ← Port protocols + adapter implementations + factory
│       │   ├── osa.py                   ← OSADataPort Protocol; mock + Databricks scaffold
│       │   ├── rgm.py                   ← RGMDataPort; mock + Databricks scaffold
│       │   ├── crm.py                   ← CRMPort; local + external HTTP adapter
│       │   ├── erp.py                   ← ERPPort; sandbox + external HTTP adapter
│       │   ├── store_master.py          ← StoreMasterPort; mock + Snowflake scaffold
│       │   ├── shelf_image.py           ← ShelfImagePort; mock + external HTTP adapter
│       │   ├── real.py                  ← shared base for live adapters
│       │   └── factory.py              ← selects adapter from *_ADAPTER env vars
│       ├── agents/
│       │   ├── state.py                 ← AgentState (Pydantic BaseModel, not TypedDict)
│       │   └── graph.py                 ← graph-style async node functions; no LangGraph dep
│       ├── api/routes/                  ← one module per domain
│       │   ├── agent.py                 ← POST /agent/osa-summary, POST /agent/run (SSE)
│       │   ├── visits.py, stores.py, alerts.py, orders.py, approvals.py
│       │   ├── manager.py, admin.py, audit.py
│       │   ├── crm.py, rgm.py, shelf_images.py, sync.py
│       │   ├── integrations.py          ← GET /integrations/readiness
│       │   ├── metrics.py               ← GET /metrics/pilot
│       │   └── health.py                ← GET /health and all sub-checks
│       ├── api/schemas.py               ← all Pydantic request/response models
│       ├── auth/
│       │   ├── mock_jwt.py              ← mock JWT decoder (no signature check)
│       │   └── providers.py             ← external JWT / JWKS provider scaffold
│       ├── clients/sql.py               ← Databricks + Snowflake HTTP SQL API clients
│       ├── db/
│       │   ├── models.py                ← SQLAlchemy async ORM (AuditEvent, AlertFeedback, …)
│       │   └── session.py               ← async session factory
│       ├── governance/
│       │   ├── discovery.py             ← assert_discovery_ready(); discovery gate checks
│       │   ├── guardrails.py            ← pattern check + external classifier scaffold
│       │   ├── rbac.py                  ← rep/store role-based access
│       │   ├── policy.py                ← read-only policy stub
│       │   ├── live_contracts.py        ← live data contract validation helpers
│       │   ├── activation.py            ← activation target + runtime command manifest
│       │   ├── action_providers.py      ← CRM/ERP action provider readiness
│       │   ├── data_platform.py         ← Databricks/Snowflake readiness
│       │   ├── offline_agent.py         ← offline inference governance scaffold
│       │   └── shelf_image.py           ← shelf image provider readiness
│       ├── memory/
│       │   ├── ports.py                 ← MemoryPort Protocol
│       │   └── adapters.py              ← NullMemoryAdapter + Mem0Adapter (HTTP)
│       └── services/
│           ├── audit.py                 ← log_audit_event(); always call this, not DB directly
│           ├── audit_sinks.py           ← AuditSink (Postgres primary, Unity Catalog dual-write)
│           ├── agent_summary.py         ← create_osa_summary(); shared by REST + agent routes
│           ├── summary.py               ← build_grounded_summary()
│           ├── summary_providers.py     ← template + Anthropic provider boundary
│           ├── rules.py                 ← action_and_confidence(), priority_reasons()
│           ├── manager_tasks.py         ← task assignment + status transitions
│           ├── feedback.py              ← alert feedback capture
│           ├── hashing.py               ← payload hash for order HITL binding
│           ├── telemetry.py             ← structured request logging + OTLP boundary
│           └── discovery.py             ← (separate from governance/) discovery-scoped helpers
│
├── frontend/
│   ├── src/App.tsx                      ← monolithic workbench: rep / manager / admin views
│   ├── src/components/TraceDrawer.tsx
│   ├── src/lib/
│   │   ├── api.ts                       ← typed fetch client + SSE helper
│   │   ├── types.ts                     ← shared TypeScript types
│   │   ├── offlineCache.ts              ← IndexedDB read cache (route, store, alerts, RGM)
│   │   └── offlineQueue.ts              ← IndexedDB feedback sync queue
│   ├── public/sw.js, manifest.webmanifest ← PWA app shell
│   └── tests/e2e/workbench.spec.ts      ← Playwright smoke (rep workbench flow)
│
├── mcp/
│   ├── runtime.py                       ← shared JSON CLI runner
│   └── osa/, rgm/, crm/, orders/, store_master/, shelf_image/, manager/
│       ├── server.py                    ← entry point (calls runtime.run_cli)
│       └── tools.py                     ← tool functions (delegate to backend adapter factory)
│
├── infra/databricks/audit_table_ddl.sql ← Unity Catalog DDL (not yet live)
├── scripts/                             ← eval, readiness, smoke, handoff scripts
└── docs/                                ← planning, compliance, corrections, runbooks, visual briefs
```

---

## Setup Commands

```powershell
# Backend — run from phantom/backend/
python -m venv .venv
. .venv/Scripts/Activate.ps1      # Windows PowerShell
# source .venv/bin/activate        # macOS / Linux bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend — run from phantom/frontend/
npm ci
npm run build
npx playwright install --with-deps chromium
```

---

## Verification Commands

Run all of these before every commit. CI runs them in the same order.

For a single repo-root runner that records public-safe artifacts:

```powershell
# From phantom/ (repo root)
python scripts/verify_local.py --include-frontend-e2e
```

Use the expanded command list below when debugging a specific failing gate:

```powershell
# From phantom/backend/
python -m ruff check backend tests alembic ../mcp ../scripts
python -m pytest tests -q
python ../scripts/run_eval.py
python ../scripts/pilot_readiness_report.py --target local
python ../scripts/validate_live_data_contracts.py --manifest-only
python ../scripts/mcp_smoke.py
python ../scripts/readiness_bundle.py --target local --output-dir ../artifacts/readiness/ci

# From phantom/frontend/
npm run build
npm run test:e2e

# From phantom/ (repo root)
bash ./scripts/public_safety_scan.sh
```

---

## Architecture Conventions

**These are the rules of this codebase. Read before writing any new code.**

### Port / Adapter / Factory

Every external data source and action goes through three layers:

```
*Port (Protocol in backend/adapters/*.py)
  → *Adapter (mock | local | sandbox | real implementation)
    → factory.py (picks adapter from *_ADAPTER env var)
```

Current adapter env vars and their safe defaults:

| Env var | Default | Notes |
|---|---|---|
| `OSA_ADAPTER` | `mock` | Databricks adapter scaffolded in `adapters/osa.py` |
| `RGM_ADAPTER` | `mock` | Databricks adapter scaffolded in `adapters/rgm.py` |
| `STORE_MASTER_ADAPTER` | `mock` | Snowflake adapter scaffolded in `adapters/store_master.py` |
| `CRM_ADAPTER` | `local` | External HTTP adapter in `adapters/crm.py` |
| `ERP_ADAPTER` | `sandbox` | External HTTP adapter in `adapters/erp.py` |
| `SHELF_IMAGE_ADAPTER` | `mock` | External HTTP adapter in `adapters/shelf_image.py` |

**Never** call Databricks, Snowflake, CRM, ERP, or shelf-image endpoints directly from
route handlers or service functions. Always go through the adapter factory.

### REST Routes and MCP Tools Share the Same Logic

A REST route and its corresponding MCP tool must call the **same** adapter and service
functions. Never duplicate scoring, alert selection, approval, audit, or policy logic.

See `docs/spec-compliance.md` (MCP Tool Function Mapping) for the current shared-logic map.

### Audit Writes Go Through AuditSink

Never write audit rows directly to the database from a route or agent node. Always call
`services/audit.py → log_audit_event(...)`. This delegates to `services/audit_sinks.py →
get_audit_sink()`, which is config-selectable (`AUDIT_SINK`, `AUDIT_DUAL_WRITE_ENABLED`,
`AUDIT_UNITY_CATALOG_TABLE`).

### Every Live Integration Must Pass Discovery Gates

Before any live external integration can be activated, the relevant `DISCOVERY_*` env vars
must be filled, `/integrations/readiness` must show it as unblocked, and a credentialed
smoke or dry-run artifact must exist.

`governance/discovery.py → assert_discovery_ready(...)` enforces this at adapter
construction time. Do not remove or bypass these checks.

### Feature Flags Gate Everything Not Yet Production-Ready

New capabilities go behind a feature flag in `config.py`. The default must be the
safe/mock value. Document every new flag in `.env.example` with a comment.

### Agent Graph Functions Are Plain Async Functions

`agents/graph.py` contains graph-style node functions (`async def *_node`) but installs
**no LangGraph dependency**. `AGENT_GRAPH_ENABLED` gates whether the agent endpoint uses
graph routing or a direct service call. Do not add the `langgraph` package unless the
continuation plan explicitly activates it.

### No SQL String Interpolation

All Databricks and Snowflake adapter code must use parameterized query builders
(`clients/sql.py → QueryStatement`), not f-strings or `%` formatting. See
`docs/spec-corrections.md` correction 3.

---

## Feature Flags and Current Defaults

| Flag | Default | Change to |
|---|---|---|
| `SUMMARY_PROVIDER` | `template` | `anthropic` for AI demo after eval validation |
| `AGENT_GRAPH_ENABLED` | `false` | `true` to use graph routing in /agent/osa-summary |
| `AGENT_RUN_ENABLED` | `true` | — |
| `AUTH_MODE` | `mock_jwt` | `external_jwt` after SSO discovery completes |
| `MEMORY_PROVIDER` | `none` | `mem0` after discovery gates pass |
| `AUDIT_SINK` | `postgres` | Keep; enable `AUDIT_DUAL_WRITE_ENABLED` for Unity Catalog |
| `GUARDRAIL_PROVIDER` | `pattern` | `external` after classifier endpoint is confirmed |
| `OFFLINE_AGENT_ENABLED` | `false` | Hermes/Ollama; behind kill-switch |
| `AI_DEMO_EVAL_VALIDATED` | `false` | `true` only after running eval with real Anthropic provider |

---

## Locked Technology Decisions

These decisions are final for this implementation phase.

| Area | Decision |
|---|---|
| LLM SDK | Official `anthropic` Python SDK only. No LangChain LLM wrappers. |
| Default model | `claude-haiku-4-5`, configurable via `ANTHROPIC_MODEL` |
| Agent orchestration | Plain async node functions. LangGraph not required for Phase 1 (spec correction #9). |
| Generative UI | Custom `/agent/run` SSE bridge. CopilotKit formally replaced, not just deferred (spec correction #10). |
| Memory | `MemoryPort` with `NullMemoryAdapter` default. Mem0 discovery-gated. |
| Audit persistence | `AuditSink` → Postgres primary. Unity Catalog dual-write scaffolded, not active. |
| MCP transport | Local JSON CLI. FastMCP SSE deferred until live data sources are confirmed. |
| Database | SQLite (local/test), PostgreSQL (prod), via SQLAlchemy async + Alembic. |
| Frontend | React 18 + Vite, plain CSS. No CopilotKit, no Zustand, no Tailwind yet. |
| Python | 3.11+ |

---

## Deferred Technology — Do Not Add

These are scaffolded or planned but must **not** be added as installed dependencies
unless a specific plan chunk explicitly activates them.

- **LangGraph** — no `langgraph` package. Plain async functions are the Phase 1 architecture (spec correction #9). Activate only if pilot evidence requires durable graph state.
- **CopilotKit / AG-UI** — permanently replaced by the custom SSE bridge for Phase 1 (spec correction #10). Do not add unless client explicitly requests generative UI components.
- **FastMCP (SSE transport)** — MCP tools use local JSON CLI. FastMCP SSE is deferred.
- **mem0ai package** — Mem0 adapter uses `httpx` directly; the SDK package is not installed.
- **Hermes 3 / Ollama** — offline inference is behind `OFFLINE_AGENT_ENABLED=false`.
- **LangSmith exporters** — structured local logs are the default; OTLP boundary is scaffolded.
- **Managed MLflow tracking server** — local eval harness emits MLflow-ready artifacts only.
- **Unity Catalog live writes** — parameterized insert path exists; dual-write is off by default.
- **Tailwind CSS** — frontend currently uses plain CSS; do not add until a plan chunk says to.

---

## Permanent Spec Corrections

These override the original MVP spec. Full list in `docs/spec-corrections.md`.

1. `store_master` includes `promo_compliance_rate` and `revenue_opportunity_score`.
2. `oos_risk` includes `territory_code` and `rep_id` (reads are identity-scoped).
3. No SQL string interpolation — use parameterized query builders everywhere.
4. The OSA agent pseudocode in the spec (iterating `response.content` for tool messages)
   is invalid. Phase 1 keeps deterministic data retrieval outside the LLM call path.
5. Phase 1 UX is workbench-first. Copilot-style chat is secondary.
6. Audit data is append-only. Approval decisions live in separate append-only rows.
7. Read paths set `requires_approval=false`. Approval gates apply to write actions only (Phase 2+).
8. There is no `backend/mcp_servers/` directory. MCP servers live under `mcp/`.
   Backend adapters live under `backend/adapters/`. Backend HTTP clients live under
   `backend/clients/`.
9. LangGraph is not a required dependency for Phase 1. The plain async node functions
   behind `AGENT_GRAPH_ENABLED=false` are the production orchestration layer for the
   pilot. Do not install `langgraph` until the pilot produces evidence that durable
   multi-turn graph state is needed.
10. CopilotKit is permanently replaced by the custom `/agent/run` SSE bridge for
    Phase 1. Do not install `@copilotkit/*` packages unless the client explicitly
    requests generative UI components — this is not a spec gap to close, it is a
    deliberate architectural decision.

---

## Public Safety Rules

These apply to every commit with no exceptions.

- Never commit secrets, API keys, bearer tokens, or credentials of any kind.
- Never commit `phantom.db` or any other local database file.
- Never commit screenshots, internal client presentations, or internal planning documents.
- Never commit absolute machine paths (for example, local Windows or Unix home-directory paths).
- Never commit internal client names or confidential project references in public-facing files.
- The internal MVP specification is an external document — it must never be committed here.
- Run `bash ./scripts/public_safety_scan.sh` before every commit. It must pass with no findings.

---

## Before Implementing Any New Spec Area

1. Read `docs/spec-compliance.md` → find the row for the area you are about to implement.
   Understand what is already built and what is deliberately deferred.
2. Read `docs/implementation-continuation-plan.md` → confirm this area is the next chunk
   in order. Implement chunks in order unless the area is clearly independent.
3. Read `docs/spec-corrections.md` → check whether the spec section you are implementing
   has a correction that overrides the original text.
4. Check `.env.example` → confirm whether the area needs a new feature flag and what its
   safe default should be.

## When Changing Existing Behavior

Update `docs/spec-compliance.md` **in the same commit** as the code change. Do not let
compliance posture drift from the implementation. If tests change, explain why in the
commit message.

## Per-Task Done Checklist

A task is complete only when all of the following pass locally and in CI.

- [ ] `python -m ruff check` — zero lint errors
- [ ] `python -m pytest tests -q` — all tests pass
- [ ] `python ../scripts/run_eval.py` — eval harness passes
- [ ] `python ../scripts/pilot_readiness_report.py --target local` — local scaffold green
- [ ] `python ../scripts/mcp_smoke.py` — all MCP tools registered
- [ ] `bash ./scripts/public_safety_scan.sh` — zero findings
- [ ] `python scripts/verify_local.py --include-frontend-e2e` — repo-root verification artifact generated before push when browser deps are installed
- [ ] `npm run build` — frontend builds cleanly
- [ ] `npm run test:e2e` — Playwright smoke passes
- [ ] `docs/spec-compliance.md` updated if spec posture changed
- [ ] `.env.example` updated if new settings were added
- [ ] No more than 5 substantial implementation passes before committing
