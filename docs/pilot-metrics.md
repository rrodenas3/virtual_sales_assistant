# Phase 1 Pilot Metrics

## Event Names

- `visit_priority_read`
- `store_detail_read`
- `oos_alerts_read`
- `alert_feedback_created`
- `osa_summary_created`
- `rgm_recommendations_read`
- `order_draft_created`
- `order_draft_approved`
- `order_draft_rejected`
- `crm_visit_log_draft_created`

## OSA Alert Precision

Manual audit sample:

```sql
SELECT alert_id, store_id, sku_id, rep_id, feedback, created_at
FROM alert_feedback
WHERE feedback IN ('confirmed', 'false_positive')
ORDER BY created_at DESC
LIMIT 50;
```

Precision:

```sql
SELECT
  SUM(CASE WHEN feedback = 'confirmed' THEN 1 ELSE 0 END)::float
  / NULLIF(SUM(CASE WHEN feedback IN ('confirmed', 'false_positive') THEN 1 ELSE 0 END), 0) AS precision
FROM alert_feedback;
```

## Visit Priority Hit Rate

Use confirmed alerts as the Phase 1 proxy for a recommended store having a real issue.

```sql
SELECT store_id, COUNT(*) AS confirmed_alerts
FROM alert_feedback
WHERE feedback = 'confirmed'
GROUP BY store_id
ORDER BY confirmed_alerts DESC;
```

## Trace Completeness

Every Phase 1 API call should create at least one audit event.

```sql
SELECT event_type, COUNT(*)
FROM audit_events
GROUP BY event_type
ORDER BY event_type;
```

## Hallucination Check

For each `osa_summary_created` event, validate that every SKU named in the summary is present in the logged `grounded_alert_ids` set. The automated test suite checks the deterministic summary builder.

## Latency

Use `scripts/load_test.py` for `/api/v1/agent/osa-summary`; target p95 is below 5 seconds.

## Cost Per Interaction

Phase 3 starts with estimated local telemetry on `osa_summary_created`.

```sql
SELECT
  AVG((payload_json->>'estimated_cost_eur')::numeric) AS avg_cost_eur
FROM audit_events
WHERE event_type = 'osa_summary_created';
```

## API Rollup

The local implementation exposes a pilot rollup for demo and QA:

```text
GET /api/v1/metrics/pilot
```

The response includes feedback counts, confirmed/false-positive counts, alert precision,
summary count, average estimated summary cost, and trace event counts.
