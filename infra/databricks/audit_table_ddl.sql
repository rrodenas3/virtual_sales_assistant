-- PHANTOM client-pilot Unity Catalog audit schema.
-- Append-only by policy: do not UPDATE or DELETE rows from these tables.

CREATE SCHEMA IF NOT EXISTS phantom.audit;

CREATE TABLE IF NOT EXISTS phantom.audit.agent_actions (
  event_id STRING NOT NULL,
  session_id STRING NOT NULL,
  rep_id STRING NOT NULL,
  territory_code STRING,
  event_type STRING NOT NULL,
  resource_type STRING NOT NULL,
  resource_id STRING,
  tool_name STRING,
  tool_input VARIANT,
  tool_output VARIANT,
  reasoning_trace STRING,
  model_id STRING,
  model_version STRING,
  requires_approval BOOLEAN NOT NULL,
  approval_status STRING,
  risk_level STRING,
  source_system STRING,
  data_freshness_ts TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  mlflow_run_id STRING
)
USING DELTA
TBLPROPERTIES (
  delta.appendOnly = true,
  delta.enableChangeDataFeed = true
);

CREATE TABLE IF NOT EXISTS phantom.audit.approval_decisions (
  approval_id STRING NOT NULL,
  draft_id STRING NOT NULL,
  approved BOOLEAN NOT NULL,
  approved_by STRING NOT NULL,
  draft_payload_hash STRING NOT NULL,
  notes STRING,
  created_at TIMESTAMP NOT NULL
)
USING DELTA
TBLPROPERTIES (
  delta.appendOnly = true,
  delta.enableChangeDataFeed = true
);
