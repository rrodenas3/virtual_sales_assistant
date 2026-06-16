# PHANTOM VSA — Unified Platform Infographic (5th)
# Brief: Text, Structure, and Data for the Unified Architecture Visual

This document is the complete content brief for the 5th infographic.
It ties together the four domain infographics (VSA, Know Your Store,
Assortment Mentalization, Agentic E-Commerce) into one unified platform view.
All numbers, thresholds, and code references are grounded in the actual implementation.

---

## PLATFORM IDENTITY PANEL
*(Top-center hero block)*

**Primary title:** PHANTOM VSA

**Acronym expansion — render each letter as a badge:**
```
P — Perfect Store
H — Human-in-the-Loop
A — Agentic
N — Navigation
T — Traceability
O — On-Shelf Availability
M — Mesh
```

**Tagline:**
One governed multi-agent platform. Four intelligence domains. Zero unverified writes.

**Platform descriptor:**
PHANTOM VSA is a CPG field sales intelligence platform that unifies visit
prioritization, store knowledge, assortment intelligence, and agentic order
execution under a single governed workflow. Every action is grounded in ML
model output, verified by a human, bound to an immutable audit record, and
traceable from data source to ERP submission.

---

## BAND 1 — THE THREE ROLES
*(Top horizontal band — three columns)*

### FIELD REPRESENTATIVE
**Entry point:** Daily ranked visit route — 25 stores, scored every session

**What they see:**
- Visit priority list with explainable score breakdown per store
- Store 360° view: tier, revenue (€), promo compliance rate, OOS SKU count, data freshness
- Grounded OOS alerts: risk score, phantom inventory flag, predicted stockout date, recommended action
- AI-generated summary grounding all active alerts to one actionable narrative
- RGM action band: promo move, assortment gap, upsell opportunity per store
- One-tap order draft → HITL approval gate
- Task inbox from manager

**Session state:** `session_id · rep_id · territory_code · role=rep`

---

### TERRITORY MANAGER
**Entry point:** Territory command view — all stores ranked, all reps visible

**What they see:**
- Territory summary: total OOS alerts, confirmed feedback count, open draft count, false positive rate
- Per-store priority scores and rep assignment
- Pending approval queue: all order drafts with payload preview + hash fingerprint
- One-tap approve/reject with tamper detection (hash mismatch blocks approval)
- Task assignment panel: shelf check, follow-up, promo check, order review — per rep, per store
- Live provider readiness: which integrations are active, which are blocked

**Session state:** `session_id · manager_id · territory_code · role=manager`

---

### PLATFORM ADMINISTRATOR
**Entry point:** Governance console — full audit trail, real-time event feed

**What they see:**
- Append-only audit event stream: every read, write, approval, and rejection with full payload
- Event drilldown: provider, model_id, token cost (€), latency_ms, orchestration_mode,
  memory_provider, grounding_result
- Integration readiness dashboard: 3 activation targets (local scaffold · AI demo · pilot),
  per-provider blockers, discovery gate answers by owner (delivery vs. engineering)
- Pilot precision metrics: alert_precision, false_positive_count, avg_cost_eur, summary_count
- Unity Catalog audit mirror status (dual-write mode, DDL drift check)

**Session state:** `session_id · admin_id · role=admin`

---

## BAND 2 — PRESENTATION LAYER
*(Second horizontal band — full width)*

**Layer label:** React 18 Progressive Web App

**Technology stack:**
```
React 18 + Vite
Plain CSS (no Tailwind dependency)
IndexedDB offline cache (routes · stores · alerts · RGM)
IndexedDB feedback sync queue (submit on reconnect)
Service worker app shell (static asset caching)
PWA manifest (installable on mobile device)
SSE client (Server-Sent Events agent stream)
Typed fetch API client (all 16 router endpoints)
```

**Three workbench views:**
```
┌─────────────────────────────────────────────┐
│  REP WORKBENCH                              │
│  Visit Route → Store Detail → Alert Feed   │
│  → Agent Summary → Draft Order             │
├─────────────────────────────────────────────┤
│  MANAGER COMMAND VIEW                       │
│  Territory Summary → Approval Queue →       │
│  Task Assignment → Integration Readiness    │
├─────────────────────────────────────────────┤
│  ADMIN GOVERNANCE CONSOLE                   │
│  Audit Feed → Event Detail →                │
│  Pilot Metrics → Provider Readiness         │
└─────────────────────────────────────────────┘
```

**Offline capability:**
```
ONLINE MODE                    OFFLINE MODE (auto-detected)
All data from live API         Reads served from IndexedDB cache
Writes commit immediately      Alert feedback queued locally
                               Queue auto-drains on reconnect
                               Orders and approvals require connectivity
```

---

## BAND 3 — ORCHESTRATION CORE
*(Central highlight band — the brain of the platform)*

**Band label:** Agent Orchestration + HITL Gate

### Agent State (data capsule)
```
AgentState
──────────────────────────────────
session_id       string
rep_id           string
role             rep | manager | admin
territory_code   string
store_id         string | null
visit_date       date | null
alert_ids        string[] | null
visits           VisitPriority[]
alerts           OOSAlert[]
summary          string | null
hitl             HITLState
──────────────────────────────────
HITLState
  required       bool
  reason         string | null
  resume_token   string | null
```
Source: `backend/agents/state.py`

### Four Node Functions (pipeline flow)
```
visit_priority_node
  → osa.get_visit_priority(rep_id, territory_code, visit_date)
  → returns ranked store list with priority scores
        ↓
grounded_alerts_node
  → osa.get_alerts_by_ids(rep_id, territory_code, alert_ids)
  → validates alert ownership and store scope
        ↓
summary_node
  → memory.get_context(rep_id, store_id)      ← inject past session context
  → get_summary_provider().summarize(alerts)   ← LLM or template
  → log_audit_event("osa_summary_created")     ← immutable record
  → memory.record_interaction(...)             ← persist for next session
        ↓
order_hitl_node
  → HITLState(required=True,
               reason="order_draft_requires_human_approval",
               resume_token="{session_id}:hitl:order")
  → NO write executes until human approval confirmed
```
Source: `backend/agents/graph.py`

### Summary Provider Gate (fork)
```
SUMMARY_PROVIDER
      │
      ├── template (default, no LLM)
      │     deterministic grounded text · zero token cost · always available
      │
      └── anthropic (AI demo + pilot)
            claude-haiku-4-5 (configurable via ANTHROPIC_MODEL)
            official Anthropic Python SDK
            token cost tracked in EUR, logged to audit
            latency_ms recorded per call
            grounding_result: grounded | no_alerts | provider_fallback
            fail_open: falls back to template on provider error
```
Source: `backend/services/agent_summary.py`, `backend/services/summary_providers.py`

### Guardrail Checkpoint (gate before every LLM call)
```
check_guardrails(input_text)
      │
      ├── PatternGuardrailProvider (always active)
      │     6 blocked patterns — hardcoded blocklist
      │     instant, no network, zero cost
      │
      └── ExternalClassifierGuardrailProvider (discovery-gated)
            POST {GUARDRAIL_CLASSIFIER_ENDPOINT}
            risk_score threshold: 0.85
            fail_closed: configurable
            → blocked → 400, reason logged to audit
            → allowed → proceed to LLM call
```
Source: `backend/governance/guardrails.py`

### SSE Streaming Bridge
```
POST /agent/run  (AGENT_RUN_ENABLED=true)
  → Server-Sent Events stream
  → Events: session_started · grounded_alerts · summary_chunk
             hitl_required · session_complete · error
  → Frontend renders event timeline in real time
```
Source: `backend/api/routes/agent.py`

---

## BAND 4 — FOUR INTELLIGENCE DOMAINS
*(Four equal quadrants — each maps to one infographic)*

### DOMAIN 1 · VISIT INTELLIGENCE
*Infographic 1 = Virtual Sales Assistant*

**Priority scoring formula:**
```
priority_score = 0.4 × oos_risk
               + 0.3 × promo_gap
               + 0.2 × revenue_opportunity
               + 0.1 × visit_recency

Output per store:
  store_id · store_name · address
  priority_score (0.0–1.0) · rank (integer)
  reasons[] (plain-English per component)
  components { oos_risk · promo_gap · revenue_opportunity · visit_recency }
  oos_sku_count · data_freshness_ts
```

**Stale data gate:** `data_freshness_ts > 24h` → action overridden to
"Validate before acting" regardless of risk score

**Connection:** Priority score is computed from the same OSA and RGM data
that powers Domain 2 and Domain 3.

Source: `backend/services/rules.py`, `backend/adapters/osa.py`

---

### DOMAIN 2 · STORE INTELLIGENCE
*Infographic 2 = Know Your Store*

**Store 360° fields:**
```
store_id · store_name · retailer_name · address
store_tier (A | B | C) · territory_code · rep_id
last_visit_date · next_visit_date
units_sold_30d · revenue_30d (€)
promo_compliance_rate (0.0–1.0)
revenue_opportunity_score (0.0–1.0)
oos_sku_count · data_freshness_ts
```

**OOS alert rule engine:**
```
OSA ML model output per SKU × store:
  risk_score (0.0–1.0) · is_phantom_inventory (bool)
  predicted_stockout_date · root_cause_label

action_and_confidence():
  risk ≥ 0.9               → "Prioritize shelf check" · HIGH
  phantom + risk ≥ 0.85    → "Verify backroom; escalate phantom" · HIGH
  0.7 ≤ risk < 0.9         → "Confirm on-shelf availability" · MEDIUM
  default                  → "Monitor during next visit" · LOW
  data > 24h stale         → "Validate before acting" · LOW (overrides all)
```

**Rep feedback loop:**
```
Values: confirmed | false_positive | dismissed | needs_follow_up
Idempotency key prevents duplicate offline submissions
Pilot metric: alert_precision = confirmed / (confirmed + false_positive)
```

Source: `backend/services/rules.py`, `backend/adapters/osa.py`, `backend/services/feedback.py`

---

### DOMAIN 3 · ASSORTMENT INTELLIGENCE
*Infographic 3 = Assortment Mentalization*

**Three RGM output types per store:**
```
PromoRecommendation
  sku_id · promo_name · expected_lift (%) · margin_impact (€)
  reason · confidence_label (low | medium | high)

AssortmentGap
  sku_id · sku_name · category
  estimated_revenue_opportunity (€)
  reason · confidence_label

UpsellOpportunity
  sku_id · sku_name · estimated_value (€)
  reason · confidence_label
```

**Shared inputs from OSA layer:**
- `revenue_opportunity_score` — same field used in Domain 1 priority formula
- `promo_compliance_rate` — same field in Store 360° view
- RGM adapter scores each type using both inputs
- Audit event: `rgm_recommendations_read` (promo_count, gap_count, upsell_count)

**Architecture note:** `RGM_ADAPTER` and `OSA_ADAPTER` share the same Databricks
discovery gate. Flipping one to `databricks` unblocks the same credential path for both.

Source: `backend/adapters/rgm.py`, `backend/api/routes/rgm.py`

---

### DOMAIN 4 · AGENTIC ORDER EXECUTION
*Infographic 4 = Agentic E-Commerce*

**Full HITL pipeline:**
```
Step 1 · DRAFT
  POST /api/v1/orders/drafts
  → stable_payload_hash(payload) = SHA-256 of canonical JSON
  → OrderDraft { draft_id, status=PENDING, payload_hash }
  → log_audit_event("order_draft_created", payload_hash)

Step 2 · APPROVE  (manager only, territory-scoped RBAC)
  POST /api/v1/approvals/{draft_id}/approve
  → ApprovalRecord { approval_id, draft_id, draft_payload_hash }
  → OrderDraft.status → APPROVED
  → log_audit_event("order_approved", draft_payload_hash)

Step 3 · SUBMIT
  POST /api/v1/orders/drafts/{draft_id}/submit-sandbox
  → verify draft.status == APPROVED
  → verify ApprovalRecord.draft_payload_hash == draft.payload_hash
  → hash mismatch → 409 CONFLICT (tamper detected, ERP call blocked)
  → hash match → erp.submit_order(payload)
  → log_audit_event("order_sandbox_submitted", erp_order_id)
```

**Tamper-proof guarantee:** SHA-256 hash computed at draft creation, stored in
both draft and approval records, verified again at submission. Any post-approval
modification produces a hash mismatch and blocks the ERP call at the protocol level.

Source: `backend/api/routes/orders.py`, `backend/services/hashing.py`

---

## BAND 5 — THE SKILL LAYER (MCP MESH)
*(Five band — 7 server nodes sharing the same adapter layer)*

**Band label:** 7 MCP Tool Servers — All Backed by the Same Adapter Layer

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   OSA    │ │   RGM    │ │  ORDERS  │ │   CRM    │ │  STORE   │ │  SHELF   │ │ MANAGER  │
│  server  │ │  server  │ │  server  │ │  server  │ │  MASTER  │ │  IMAGE   │ │  server  │
├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤
│visit_    │ │promo_    │ │create_   │ │preview_  │ │get_store │ │analyze_  │ │preview_  │
│priority  │ │recs      │ │draft     │ │visit_log │ │detail    │ │shelf     │ │task_     │
│oos_      │ │assort_   │ │preview_  │ │          │ │list_     │ │          │ │payload   │
│alerts    │ │gaps      │ │payload   │ │          │ │stores    │ │          │ │          │
│phantom_  │ │upsell_   │ │          │ │          │ │          │ │          │ │          │
│inventory │ │ops       │ │          │ │          │ │          │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
                     ↓ SHARED ADAPTER FACTORY (factory.py @lru_cache) ↓
```

**Critical architecture rule:**
```
REST route           →  same service function  ←  MCP tool
/agent/osa-summary   →  create_osa_summary()  ←  osa_server.visit_priority
/stores/{id}/alerts  →  osa.get_alerts()      ←  osa_server.oos_alerts
/orders/drafts       →  orders service        ←  orders_server.create_draft
```
No logic duplication. One source of truth per domain.

**Current transport:** Local JSON CLI (tools callable from within the same Python process)
**Deferred transport:** FastMCP SSE — standalone HTTP servers callable from external
agents and Snowflake Cortex (pending live data confirmation)

Source: `mcp/*/server.py`, `mcp/*/tools.py`, `mcp/runtime.py`

---

## BAND 6 — THE DATA LAYER
*(Sixth band — Port/Adapter/Factory pattern)*

**Band label:** 6 Data Ports · 14 Adapters · One Factory

```
OSA PORT           RGM PORT           STORE MASTER       CRM PORT           ERP PORT           SHELF IMAGE
OSADataPort        RGMDataPort        StoreMasterPort    CRMPort            ERPPort            ShelfImagePort
───────────        ───────────        ───────────        ───────────        ───────────        ───────────
[OSA_ADAPTER]      [RGM_ADAPTER]      [STORE_MASTER_     [CRM_ADAPTER]      [ERP_ADAPTER]      [SHELF_IMAGE_
=mock|databricks   =mock|databricks   ADAPTER]           =local|external    =sandbox|          ADAPTER]
                                      =mock|snowflake                       external           =mock|external
───────────        ───────────        ───────────        ───────────        ───────────        ───────────
Mock               Mock               Mock               Local              Sandbox            Mock
Adapter            Adapter            Adapter            CRM                ERP                Adapter
25 stores,         formula-driven,    seeded             (local DB          (fake              (findings from
125 alerts,        1 rec/type         store data         drafts)            erp_order_id)      alerts)
deterministic      per store          only)
───────────        ───────────        ───────────        ───────────        ───────────        ───────────
Databricks         Databricks         Snowflake          External           External           External
OSA Adapter        RGM Adapter        StoreMaster        CRM Adapter        ERP Adapter        HTTP Adapter
(SQL API,          (SQL API,          Adapter            (httpx,            (httpx,            (httpx,
parameterized      parameterized      (Snowflake SQL      approval_id,       payload_hash,      image_ref,
QueryStatement)    QueryStatement)    API, semantic       hash binding)      discovery-         discovery-
                                      views)                                gated)             gated)
```

**Discovery gate rule:** `assert_discovery_ready(topic)` fires at adapter construction.
Missing `DISCOVERY_*` env vars block adapter construction immediately — no silent
fallback to mock when live data was intended.

Source: `backend/adapters/factory.py`, `backend/governance/discovery.py`

---

## BAND 7 — THE GOVERNANCE HARNESS
*(Bottom — wraps all 6 bands as a frame. Governance is not a layer; it is the operating condition.)*

**Band label:** Governance Harness — Every Layer, Every Request

### Control 1 · Discovery Gates
```
Topics: databricks · snowflake · sso · crm_writeback · erp_submit
        shelf_image · unity_catalog · guardrail_classifier
Status per topic: answered | defaulted | missing
Owner: delivery | engineering | shared
Gate fires at: adapter construction (not first query)
```

### Control 2 · Role-Based Access Control
```
Every request:
  assert_territory_access(current_user, territory_code)
  assert_store_access(current_user, store_id)
  Rep:     own stores only
  Manager: approve/reject within their territory
  Admin:   read all audit events, all territories
```

### Control 3 · Guardrails
```
Every LLM input:
  Pattern check (always on):     6 blocked phrases, instant, no network
  External classifier (gated):   risk_score ≥ 0.85 → blocked
                                  fail_closed: configurable
  On block: 400 response + audit event. LLM call never made.
```

### Control 4 · Audit Sink
```
Every action → log_audit_event() → AuditSink → get_audit_sink()
  Sink options:
    AUDIT_SINK=postgres              (default, always active)
    AUDIT_DUAL_WRITE_ENABLED=false   (Unity Catalog DDL exists, pending credentials)
  Append-only: no update or delete paths exist anywhere in the codebase
```

### Control 5 · Payload Hash Binding
```
stable_payload_hash(payload) = SHA-256 of canonical JSON
Stored in: OrderDraft.payload_hash
Stored in: ApprovalRecord.draft_payload_hash
Verified at: ERP submit — mismatch → 409 CONFLICT
Result: no approved order can be modified before ERP submission
```

### Control 6 · Feature Flags
```
SUMMARY_PROVIDER       template | anthropic
AGENT_GRAPH_ENABLED    false | true
AGENT_RUN_ENABLED      true | false
AUTH_MODE              mock_jwt | external_jwt
MEMORY_PROVIDER        none | mem0
AUDIT_DUAL_WRITE       false | true
GUARDRAIL_PROVIDER     pattern | external
OFFLINE_AGENT_ENABLED  false | true
OSA_ADAPTER            mock | databricks
RGM_ADAPTER            mock | databricks
ERP_ADAPTER            sandbox | external
CRM_ADAPTER            local | external
Default: always the safe, mock, or local value
```

### Control 7 · Memory Layer
```
MemoryPort (Protocol)
  NullMemoryAdapter (MEMORY_PROVIDER=none, default)
    get_context()          → empty dict
    record_interaction()   → no-op
  Mem0Adapter (MEMORY_PROVIDER=mem0, discovery-gated)
    httpx POST to Mem0 HTTP API (no SDK package installed)
    Scope: rep_id + store_id
    get_context:           retrieves prior session summaries
    record_interaction:    persists event_type, summary, alert_count
    Injected into LLM:     "Context from previous visits: ..."
    Failure:               non-fatal, telemetry-logged, does not block summary
```

### Control 8 · Activation Targets
```
LOCAL SCAFFOLD          AI DEMO                 FULL PILOT
───────────────         ───────────────         ───────────────
All mock adapters       SUMMARY_PROVIDER=       Live data adapters
PWA installable         anthropic               Real SSO (JWT)
HITL flow runs          Eval validated          Real ERP/CRM writes
Audit trail live        AI_DEMO_EVAL_           Unity Catalog audit
MCP smoke passes        VALIDATED=true          Discovery answered
Public safety green     Template mode           Guardrail classifier
                        blocked for AI          connected
                        validation
```

---

## THE UNIFIED FLOW NARRATIVE
*(End-to-end swimlane — one session across all 5 bands)*

**Title:** One Session. Five Layers. Zero Unverified Writes.

```
REP opens app (offline-capable PWA)
          │
          ▼
AgentState initialized { session_id, rep_id, territory_code, role=rep }
          │
          ▼
visit_priority_node
  → osa.get_visit_priority(rep_id, territory_code, today)
  → priority = 0.4×OOS + 0.3×promo_gap + 0.2×revenue_opp + 0.1×recency
  → 25 stores ranked, reasons[] per store
  → Audit: visit_priority_read
          │
          ▼
Rep selects store
  → osa.get_store_detail(store_id)
  → osa.get_oos_alerts(store_id) → rule engine per alert
  → rgm.get_recommendations(store_id) → promo + gap + upsell
  → Audit: store_detail_read · alert_read · rgm_recommendations_read
          │
          ▼
Rep requests AI summary
  → check_guardrails(alert_ids)              — pattern check
  → grounded_alerts_node                     — validates ownership
  → memory.get_context(rep_id, store_id)     — prior session context
  → get_summary_provider().summarize(alerts) — template or claude-haiku-4-5
  → SSE stream → frontend renders event-by-event
  → Audit: osa_summary_created { model_id, tokens, cost_eur, latency_ms }
  → memory.record_interaction(summary, alert_count, store_id)
          │
          ▼
Rep taps "Draft Order"
  → stable_payload_hash(payload) = SHA-256
  → OrderDraft { draft_id, status=PENDING, payload_hash }
  → HITLState(required=True, resume_token="{session_id}:hitl:order")
  → Audit: order_draft_created { payload_hash }
  → NO ERP call. Full stop.
          │
          ▼
MANAGER reviews approval queue
  → sees payload + hash fingerprint
  → taps "Approve"
  → ApprovalRecord { draft_id, draft_payload_hash, approved_by }
  → OrderDraft.status → APPROVED
  → Audit: order_approved { approval_id, draft_payload_hash }
          │
          ▼
System submits to ERP
  → verify draft.status == APPROVED
  → verify ApprovalRecord.draft_payload_hash == draft.payload_hash
  → mismatch → 409 CONFLICT — ERP call blocked
  → match → erp.submit_order(payload)
  → Audit: order_sandbox_submitted { erp_order_id, payload_hash, approval_id }
          │
          ▼
ADMIN sees complete audit chain
  order_draft_created → order_approved → order_sandbox_submitted
  Every event: full payload, rep_id, session_id, timestamp, hash
  Append-only. Immutable. No delete path.
```

---

## KEY METRICS PANEL

| Metric | Value | Source |
|---|---|---|
| Stores per territory | **25** | MockOSAAdapter seed (ST-001 to ST-025) |
| OOS alerts per territory | **125** | 5 alerts × 25 stores |
| Priority formula components | **4** | OOS · promo · revenue · recency |
| Formula weights | **0.4 · 0.3 · 0.2 · 0.1** | `services/rules.py` |
| Risk threshold for HIGH confidence | **≥ 0.9** | `action_and_confidence()` |
| Phantom inventory threshold | **≥ 0.85 + phantom flag** | `action_and_confidence()` |
| Stale data gate | **> 24 hours** | `action_and_confidence()` |
| Guardrail block patterns | **6** | `PatternGuardrailProvider` |
| External classifier block threshold | **0.85** | `ExternalClassifierGuardrailProvider` |
| MCP servers | **7** | OSA · RGM · CRM · Orders · Store Master · Shelf Image · Manager |
| Data ports | **6** | OSA · RGM · StoreMaster · CRM · ERP · ShelfImage |
| Total adapters | **14** | 2–3 per port |
| API routers | **16** | `backend/main.py` |
| Pydantic schemas | **40+** | `backend/api/schemas.py` |
| Agent node functions | **4** | `backend/agents/graph.py` |
| AgentState fields | **10** | `backend/agents/state.py` |
| HITL audit events per order | **3** | draft_created → approved → submitted |
| Hash algorithm | **SHA-256** | `backend/services/hashing.py` |
| Default LLM model | **claude-haiku-4-5** | `ANTHROPIC_MODEL` env var |
| Feedback values | **4** | confirmed · false_positive · dismissed · needs_follow_up |
| Activation targets | **3** | local scaffold · AI demo · full pilot |
| Spec corrections | **10** | `docs/spec-corrections.md` |
| User roles | **3** | rep · manager · admin |

---

## PLATFORM PROMISE PANEL
*(Bottom-center close)*

**Primary:**
Every insight is grounded. Every write is approved. Every action is traced.

**Three capability badges:**

`GROUNDED`
LLM output cites only ML model predictions already in the system.
No hallucinated SKUs, stores, or risk values.

`GOVERNED`
Guardrails, RBAC, discovery gates, and payload hash binding operate at every layer.
No integration activates before its governance questions are answered.

`TRACEABLE`
Every read, write, approval, and AI call produces an immutable audit record
with full payload, provider identity, token cost, and data freshness timestamp.

---

## DESIGNER NOTES

### Visual Hierarchy
```
Band 1  — Roles (narrow, 3 columns)
Band 2  — PWA (medium height)
Band 3  — Orchestration Core (LARGEST — the brain, give it most space)
Band 4  — Four domains (4 equal quadrants, each references one infographic)
Band 5  — MCP Skill Layer (7 server nodes)
Band 6  — Data Layer (6 port columns)
Band 7  — Governance Harness (frame wrapping all other bands)
```

### Color Coding
- Domain 1 (Visit Intelligence) → Blue
- Domain 2 (Know Your Store) → Green
- Domain 3 (Assortment Mentalization) → Orange
- Domain 4 (Agentic E-Commerce / HITL) → Purple
- Governance Harness → Dark charcoal (contains all colors)
- HITL path → Red accent (every write gate)
- Audit trail → Gold (immutable, always on)

### Key Visual Motif
The governance harness is not a layer — it is a frame. It should visually surround
and contain every other band, signaling that governance is not a feature but the
operating condition of the entire platform.

### Cross-References
- This is infographic 5 of 5.
- Infographics 1–4 are the four domain panels in Band 4.
- All numbers in this document are derived from the live codebase, not from the spec.
- Spec corrections #9 (LangGraph) and #10 (CopilotKit) explain what the platform
  intentionally does not use and why — see `docs/spec-corrections.md`.
