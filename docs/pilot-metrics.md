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

```powershell
python scripts/load_test.py --base-url http://localhost:8000 --requests 50 --concurrency 10 --threshold-p95-ms 5000 --output-dir artifacts/load/summary
```

The command exits non-zero if p95 exceeds the threshold or any request returns an error status. It writes `load_test_report.json` and `load_test_report.md` when `--output-dir` is supplied. By default it uses the mock pilot token; set `LOAD_TEST_BEARER_TOKEN` in the approved runtime environment to validate external identity without writing the token into artifacts.
Use `scripts/run_eval.py` for the local eval covering summary latency, grounded alert IDs, unauthorized store hiding, trace completeness, hallucination rate, provider/model metadata, and estimated cost.

Pilot gate thresholds enforced by the local eval:

- p95 summary latency: `<5s`
- hallucination rate: `0%`
- trace completeness: `100%`
- estimated interaction cost: `<€0.08`

Optional evidence artifacts:

```powershell
python scripts/run_eval.py --output-dir artifacts/eval
```

The artifact directory is intentionally untracked. It contains:

- `osa_eval_results.json`: full gate result and per-case details.
- `osa_eval_results.csv`: analyst-friendly per-case rows.
- `mlflow_metrics.json`: numeric metrics ready for MLflow logging.
- `mlflow_params.json`: provider, model, and threshold params ready for MLflow logging.

Optional MLflow handoff:

```powershell
python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval --experiment-name phantom-vsa-evals --dry-run --output-dir artifacts/eval
python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval --experiment-name phantom-vsa-evals
```

The dry run writes `mlflow_handoff.json` and `mlflow_handoff.md` without importing MLflow. Use it as the local evidence gate before a managed tracking server is available. The live logging command imports MLflow only at runtime, so CI does not require MLflow.

For AI-demo or pilot validation, require the configured AI provider explicitly:

```powershell
python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai
python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval-ai --experiment-name phantom-vsa-evals --dry-run --output-dir artifacts/eval-ai
python scripts/ai_demo_eval_evidence.py --artifact-dir artifacts/eval-ai --output-dir artifacts/eval-ai
python scripts/pilot_readiness_report.py --target ai-demo --output-dir artifacts/readiness/ai-demo
```

Template-only eval success proves scaffold safety, not final AI-assistant readiness. After the approved provider eval passes, use `ai_demo_eval.env.snippet` to record `AI_DEMO_EVAL_VALIDATED=true`, `AI_DEMO_EVAL_LAST_VALIDATION_AT`, and `AI_DEMO_EVAL_VALIDATION_SUMMARY` in the approved runtime environment so `/health/ai` and `/integrations/readiness` can distinguish configured AI from validated AI.

Every HTTP response includes `x-request-id` and `x-response-time-ms`. When `OBSERVABILITY_PROVIDER=structured`, the backend emits structured `http_request` events to the `phantom.telemetry` logger with method, path, status, request ID, and duration.

For collector integration, set `OBSERVABILITY_PROVIDER=otlp_http` and `OTEL_EXPORTER_OTLP_ENDPOINT` to the approved collector base URL. The exporter posts OTLP log records to `/v1/logs`, includes `service.name=phantom-vsa-backend`, and defaults to fail-open unless `OTEL_FAIL_CLOSED=true`.

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
