# PHANTOM VSA — Complete Commercial Workflow Explanation

This document explains how PHANTOM VSA works end-to-end from a business perspective,
framed around the real CPG commercial scenario: a brand's field rep receiving a
store-triggered signal and taking governed action before a sale is lost.

Intended use: interview preparation, stakeholder communication, onboarding.

---

## The Business Scenario

**Brand X** (e.g., Coca-Cola, Procter & Gamble, Nestlé) sells products through retail
chains. They have field sales reps whose job is to ensure their products are on the
shelf, correctly priced, and properly promoted. The problem: by the time a rep visits
a store and discovers a product is missing, the sale is already lost.

PHANTOM turns that reactive visit into a proactive intervention — triggered by data
from the store itself.

---

## The Full Chain, Step by Step

---

### LAYER 0 — The Store Sends a Signal

A local retail store generates data continuously — every scan at the till, every
inventory count, every shelf sensor reading. This data flows into the retailer's systems.

**What triggers an alert in PHANTOM:**
- A product's sell-through rate accelerates abnormally (velocity spike → shelf will empty soon)
- The inventory system shows stock exists in the warehouse but nothing is selling
  (phantom inventory — stock is recorded but not actually on the shelf)
- A promotion starts and compliance is below threshold (products aren't displayed as agreed)
- An assortment gap is detected (a core SKU is listed in the planogram but not being ordered)

**These signals flow from the retailer into the brand's data platform** — via Snowflake
Secure Data Share or Databricks Delta Share. The retailer shares their POS data,
inventory counts, and compliance metrics with Brand X under a data-sharing agreement.
Brand X's Databricks OSA model processes this data and produces, for every SKU × store:

```
oos_risk_score          0.0 → 1.0   (probability of stockout)
is_phantom_inventory    true/false   (stock exists on paper but not on shelf)
root_cause_label        distributor_delay | promotion_spike |
                        unexpected_velocity | phantom_inventory
predicted_stockout_date date         (when will the shelf be empty)
data_freshness_ts       datetime     (when was this prediction made)
```

This is the trigger. Not a phone call from the store manager. Not a rep discovering
an empty shelf. A data model detecting the risk 24–48 hours before it becomes a problem.

---

### LAYER 1 — PHANTOM Surfaces the Alert to the Right Rep

Brand X has 25 stores in the WEST-01 territory, covered by several reps. PHANTOM
routes each alert to the rep responsible for that store, scoped by territory.

When the rep opens the app, PHANTOM calculates a **priority score for every store:**

```
priority_score = 0.4 × OOS risk score
               + 0.3 × promo compliance gap
               + 0.2 × revenue opportunity score
               + 0.1 × days since last visit
```

West Market 06 scores 0.684 and ranks #1 because it has:
- High OOS risk (phantom inventory detected on Core SKU 4004)
- Promo compliance gap (the endcap promotion isn't executing)
- High revenue opportunity (€18,050 monthly revenue store)
- The visit is overdue

The rep doesn't need to decide where to go. PHANTOM tells them, with the reason
explained in plain English:

> "Moderate OOS risk across 5 SKU alerts · Promo compliance gap is material ·
> High revenue opportunity store · Visit is overdue"

---

### LAYER 2 — The Rep Understands the Situation

The rep walks into West Market 06. Before they touch a single shelf, PHANTOM shows them:

**Store 360° view:**
- €18,050 revenue in the last 30 days
- 53% promo compliance rate (poor — agreed promotions are not executing)
- 77% revenue opportunity score (store is underperforming its potential)
- Data freshness: current prediction

**5 OOS alerts, ranked by risk:**

| SKU | Category | Risk | Signal | Action |
|---|---|---|---|---|
| Core SKU 4004 | Beverages | 94% | Phantom inventory | Verify backroom — stock may be mislocated |
| Core SKU 4002 | Household | 82% | Phantom | Confirm on-shelf availability |
| Core SKU 4001 | Dairy | 76% | Unexpected velocity | Confirm on-shelf availability |
| Core SKU 4003 | Personal Care | 68% | Distributor delay | Confirm on-shelf availability |
| Core SKU 4005 | Snacks | 71% | Unexpected velocity | Monitor |

**The rep asks the AI for a summary.** PHANTOM sends only these 5 verified alerts
to Claude and receives back a grounded narrative:

> "5 shelf risks detected at West Market 06. Core SKU 4004 is the priority — the
> system shows stock in the warehouse but sell-through is near zero, suggesting the
> product is in the backroom but not on the shelf. Check the backroom before ordering
> more stock — you may just need a replenishment to the front. Promos are not
> executing on 3 SKUs: the endcap display is missing. This store has a €1,943
> revenue opportunity if assortment and compliance gaps are closed."

The AI cannot invent anything. Every word is anchored to alert data already in the
system. The model cannot produce store names, SKU IDs, or risk values that were not
injected from the verified data layer.

**RGM recommendations also appear:**
- Promo move: Weekend endcap recovery — expected lift from executing the agreed display
- Assortment gap: Core SKU 4004 not in assortment — €1,943 opportunity

---

### LAYER 3 — The Rep Takes Action

Three types of actions available:

**Action A — Alert feedback (immediate, no approval needed)**

For each OOS alert, the rep physically checks the shelf and records:
- `Confirmed` — product is missing, alert is correct
- `False positive` — product is on the shelf, model was wrong
- `Dismissed` — rep disagrees but doesn't escalate
- `Needs follow up` — more investigation needed

This feedback trains the pilot precision metric:
```
alert_precision = confirmed / (confirmed + false_positive)
```
Over time, this tells Brand X how accurate their OSA model is in this territory.

**Action B — Draft a replenishment order (requires manager approval)**

The rep builds an order:
- Core SKU 4004 × 24 units — reason: phantom inventory, verify then replenish
- Core SKU 4003 × 12 units — reason: distributor delay, proactive buffer

The system immediately:
1. Computes a SHA-256 hash of the exact order payload
2. Saves the draft with status = PENDING
3. Logs `order_draft_created` to the audit trail with the hash
4. **Stops. No ERP call. No stock movement. Human required.**

**Action C — Log the visit**

The rep records the visit outcome (completed / needs follow-up / skipped), notes,
and observations. This becomes a CRM visit log draft, audited and traceable.

---

### LAYER 4 — The Manager Reviews and Approves

The territory manager opens the **Territory command view**. They see:
- All 25 stores ranked by priority across their territory
- 125 OOS alerts outstanding across the territory
- All pending order drafts waiting for approval

They open the West Market 06 draft. They see:
- The exact items and quantities the rep drafted
- The reason the rep gave for each item
- The SHA-256 hash fingerprint of the order

If they agree → **Approve:**
- An approval record is created, independently storing the same hash
- Draft status changes to APPROVED
- `order_draft_approved` is logged to the audit trail

If they disagree → **Reject** with a reason and the rep is notified.

**Why the hash matters:**
If anyone changes the order between manager approval and ERP submission — the rep,
a system glitch, or a malicious actor — the hash at submission will not match the
hash in the approval record. The system detects this automatically and blocks the
ERP call with a 409 CONFLICT error. The order cannot be tampered with after approval.

---

### LAYER 5 — The Platform Submits to ERP

Once approved, the system executes automatically:

1. Verifies `draft.status == APPROVED`
2. Retrieves the approval record and checks `approval.hash == draft.hash`
3. Hash matches → calls the ERP adapter → replenishment order submitted to SAP / Oracle
4. Logs `order_sandbox_submitted` with ERP order ID, payload hash, and approval ID

The store receives the replenishment. The shelf gap is closed. The sale is not lost.

---

### LAYER 6 — The Admin Sees Everything

The Platform Administrator — or Brand X's compliance team — opens the
**Governance audit view**. They see, in chronological order:

```
order_draft_created     REP-001 / West Market 06 / 16/06/2026 11:13
order_draft_approved    MGR-001 / West Market 06 / 16/06/2026 11:13
order_sandbox_submitted REP-001 / ERP order confirmed / 16/06/2026 11:13
```

Every event records:
- Who did it (rep ID, manager ID)
- What they did (full payload)
- When (timestamp)
- Data freshness at the time (was the ML prediction current?)
- If AI was involved: which model, token count, cost in EUR, latency in ms

This audit trail is append-only. Nothing can be deleted or modified. Brand X can
prove to the retailer exactly what field actions were taken, when, by whom, and
on what data.

---

## The Complete Chain in One Picture

```
RETAILER STORE
POS data + inventory scans + shelf sensors
        ↓
DATABRICKS / SNOWFLAKE  (Brand X data platform)
OSA model → oos_risk_score · phantom flag · root cause · stockout date
        ↓
PHANTOM PRIORITY ENGINE
priority = 0.4×OOS + 0.3×promo + 0.2×revenue + 0.1×recency
Rep sees: ranked stores + explainable reasons per store
        ↓
FIELD REP  (in the store)
AI summary → alert feedback → order draft
        ↓  (HITL gate — ERP blocked until here)
TERRITORY MANAGER
Reviews draft → verifies hash → approves or rejects
        ↓
PLATFORM  (automatic, governed)
Hash verified → ERP adapter called → replenishment triggered
        ↓
ADMIN / BRAND COMPLIANCE
Full immutable audit: who acted, on what data, at what cost, with what result
        ↓
RETAILER STORE
Shelf restocked. Sale not lost.
```

---

## Interview Talking Points

### The 30-Second Version
> "PHANTOM VSA is a governed AI assistant for CPG field sales reps. It tells a rep
> which stores to visit first, why specific products are at risk of going out of stock,
> and lets them take action — drafting replenishment orders — with a manager approving
> every action before it hits the ERP. Everything is audited, everything is explainable,
> and no AI output executes without a human in the loop."

### Key Questions and Answers

**"How do you prevent the AI from hallucinating?"**
> "The LLM only receives alert IDs that were already retrieved and RBAC-verified from
> the OSA adapter. It can't invent data that isn't already in the system. We call this
> grounded generation — the model summarises, it doesn't create."

**"How do you ensure the approved order isn't tampered with?"**
> "We compute a SHA-256 hash of the order payload at creation. The same hash is
> independently stored in the approval record. At ERP submission we verify both match —
> any modification after approval produces a conflict and blocks the call."

**"How do you manage risk in AI deployment?"**
> "Three-stage activation ladder: local scaffold with mock data, AI demo with the real
> LLM and validated eval results, and full pilot with live data. The AI doesn't go near
> production data until the eval is validated and recorded."

**"How was this structured as a project?"**
> "Spec-Driven Development — the full product spec defined the architecture before any
> code was written. Implemented in ordered chunks with a done checklist and CI gate
> before moving to the next. Every architectural deviation from the original spec is
> formally recorded with rationale in a corrections document."

### The Commercial Value in One Sentence
> "PHANTOM converts a retailer's store-level data signal into a brand field rep's
> prioritised action, governed by a manager approval gate and an immutable audit trail —
> turning a reactive visit into a proactive intervention that closes the shelf gap
> before the sale is lost."

### What PHANTOM Stands For
> "Perfect Store · Human-in-the-Loop · Agentic · Navigation · Traceability ·
> On-Shelf Availability · Mesh. The letter I'd highlight in an interview is H —
> Human-in-the-Loop. In a world where AI is making commercial recommendations and
> initiating orders, we made governance a first-class architectural concern, not an
> afterthought."
