export type VisitPriority = {
  store_id: string;
  store_name: string;
  address: string;
  priority_score: number;
  rank: number;
  reasons: string[];
  components: {
    oos_risk: number;
    promo_gap: number;
    revenue_opportunity: number;
    visit_recency: number;
  };
  oos_sku_count: number;
  data_freshness_ts: string;
  audit_event_ids: string[];
};

export type StoreDetail = {
  store_id: string;
  store_name: string;
  retailer_name: string;
  address: string;
  store_tier: "A" | "B" | "C";
  territory_code: string;
  rep_id: string;
  last_visit_date: string | null;
  next_visit_date: string | null;
  units_sold_30d: number;
  revenue_30d: number;
  promo_compliance_rate: number;
  revenue_opportunity_score: number;
  oos_sku_count: number;
  data_freshness_ts: string;
  audit_event_id: string | null;
};

export type OOSAlert = {
  alert_id: string;
  prediction_row_id: string;
  store_id: string;
  sku_id: string;
  sku_name: string;
  category: string;
  risk_score: number;
  is_phantom_inventory: boolean;
  predicted_stockout_date: string | null;
  root_cause_label: string;
  recommended_action: string;
  confidence_label: "low" | "medium" | "high";
  data_freshness_ts: string;
  model_version: string;
  source_system: string;
  audit_event_id: string | null;
};

export type AlertFeedback = "confirmed" | "false_positive" | "dismissed" | "needs_follow_up";

export type OSASummaryResponse = {
  summary: string;
  grounded_alert_ids: string[];
  session_id: string;
  model_id: string;
  audit_event_id: string;
};

export type AgentRunEvent =
  | {
      event: "run_started";
      data: {
        run_id: string;
        session_id: string;
        intent: "osa_summary" | "order_draft" | "visit_log_draft" | "manager_task";
      };
    }
  | {
      event: "supervisor_decision";
      data: {
        run_id: string;
        intent: "osa_summary" | "order_draft" | "visit_log_draft" | "manager_task";
        agent: "osa_agent" | "action_agent";
        requires_human_approval: boolean;
      };
    }
  | {
      event: "message";
      data: { run_id: string; role: "assistant"; content: string; grounded_alert_ids: string[] };
    }
  | {
      event: "action_result";
      data: { run_id: string; type: "order_draft" | "visit_log_draft" | "manager_task"; [key: string]: unknown };
    }
  | {
      event: "hitl_required";
      data: { run_id: string; required: boolean; reason: string; resume_token: string };
    }
  | {
      event: "audit";
      data: { run_id: string; audit_event_id: string; model_id: string | null };
    }
  | {
      event: "run_completed";
      data: { run_id: string; session_id: string };
    };

export type PromoRecommendation = {
  recommendation_id: string;
  store_id: string;
  sku_id: string;
  promo_name: string;
  expected_lift: number;
  margin_impact: number;
  reason: string;
  confidence_label: "low" | "medium" | "high";
};

export type AssortmentGap = {
  gap_id: string;
  store_id: string;
  sku_id: string;
  sku_name: string;
  category: string;
  estimated_revenue_opportunity: number;
  reason: string;
  confidence_label: "low" | "medium" | "high";
};

export type UpsellOpportunity = {
  opportunity_id: string;
  store_id: string;
  sku_id: string;
  sku_name: string;
  estimated_value: number;
  reason: string;
  confidence_label: "low" | "medium" | "high";
};

export type RGMRecommendationsResponse = {
  store_id: string;
  promos: PromoRecommendation[];
  assortment_gaps: AssortmentGap[];
  upsell_opportunities: UpsellOpportunity[];
  source_system: string;
  model_version: string;
  audit_event_id: string;
};

export type OrderDraftResponse = {
  draft_id: string;
  store_id: string;
  rep_id: string;
  session_id: string;
  payload_json: {
    items?: Array<{ sku_id: string; sku_name: string; quantity: number; reason: string }>;
    notes?: string | null;
  };
  payload_hash: string;
  status: string;
  created_at: string;
  audit_event_id: string | null;
};

export type ApprovalResponse = {
  approval_id: string;
  draft_id: string;
  approved: boolean;
  approved_by: string;
  notes: string | null;
  draft_payload_hash: string;
  created_at: string;
  audit_event_id: string;
};

export type SandboxSubmitResponse = {
  draft_id: string;
  status: string;
  erp_order_id: string;
  submitted_at: string;
  approval_id: string;
  payload_hash: string;
  audit_event_id: string;
};

export type OfflineFeedbackEvent = {
  idempotency_key: string;
  alert_id: string;
  feedback: AlertFeedback;
  session_id: string;
  notes?: string | null;
};

export type PilotMetricsResponse = {
  feedback_count: number;
  confirmed_count: number;
  false_positive_count: number;
  alert_precision: number | null;
  summary_count: number;
  avg_estimated_cost_eur: number | null;
  trace_event_counts: Record<string, number>;
};

export type DiscoveryGate = {
  topic: string;
  setting_name: string;
  status: "answered" | "defaulted" | "missing";
  value: string | null;
  required_for: string[];
  notes: string;
  owner: "delivery" | "engineering" | "shared";
};

export type IntegrationReadinessResponse = {
  ready: boolean;
  selected_live_modes: string[];
  blockers: string[];
  provider_blockers: string[];
  provider_readiness: Record<string, Record<string, unknown>>;
  gates: DiscoveryGate[];
  view_contract_validated: boolean;
  last_validation_at: string | null;
  validation_summary: string | null;
  summary_provider: string;
  summary_model_id: string;
  ai_demo_ready: boolean;
  ai_demo_provider_ready: boolean;
  ai_demo_eval_validated: boolean;
  ai_demo_eval_last_validation_at: string | null;
  ai_demo_eval_validation_summary: string | null;
  ai_demo_stage: "template_scaffold" | "provider_blocked" | "provider_configured" | "validated";
  ai_demo_blockers: string[];
  ai_demo_next_actions: string[];
  ai_demo_validation_command: string | null;
  activation_targets: {
    target: "local" | "ai-demo" | "pilot";
    ready: boolean;
    description: string;
    blockers: string[];
  }[];
  runtime_validation_commands: Record<
    "local" | "ai-demo" | "pilot",
    {
      name: string;
      command: string;
      notes: string;
    }[]
  >;
  activation_evidence_manifests: Record<
    "local" | "ai-demo" | "pilot",
    {
      target: "local" | "ai-demo" | "pilot";
      sections: {
        name: string;
        required_for: Array<"local" | "ai-demo" | "pilot">;
        artifacts: string[];
        env_keys: Record<string, string>;
        notes: string;
      }[];
      required_env_keys: string[];
      required_artifacts: string[];
    }
  >;
};

export type PilotGapReport = {
  generated_at: string;
  target: "local" | "ai-demo" | "pilot";
  ready_for_requested_target: boolean;
  requested_target_blocker_count: number;
  gap_count: number;
  activation_targets: {
    target: "local" | "ai-demo" | "pilot";
    ready: boolean;
    blocker_count: number;
    blockers: string[];
  }[];
  blocking_gaps: {
    target: "local" | "ai-demo" | "pilot";
    blocker: string;
    owner: "delivery+engineering" | "engineering" | "shared";
    recommended_command_names: string[];
  }[];
  recommended_commands: {
    name: string;
    command: string;
    notes: string;
  }[];
  roadmap_items: {
    area: string;
    owner: "delivery+engineering" | "engineering" | "shared";
    status: string;
    next_gate: string;
  }[];
  public_safety_notes: string[];
};

export type ActivationRunbook = {
  generated_at: string;
  current_target: "local" | "ai-demo" | "pilot";
  final_outcome: string;
  phase_count: number;
  ready_phase_count: number;
  blocked_phase_count: number;
  phases: {
    phase_id: string;
    title: string;
    target: "local" | "ai-demo" | "pilot";
    owner: "engineering" | "delivery" | "delivery+engineering";
    estimated_effort: string;
    goal: string;
    status: "ready" | "blocked" | "scaffolded" | "deferred";
    required_command_names: string[];
    required_configuration_keys: string[];
    exit_gate_summary: string[];
    blockers: string[];
  }[];
  public_safety_notes: string[];
};

export type DiscoveryPacket = {
  generated_at: string;
  target: "local" | "ai-demo" | "pilot";
  selected_live_modes: string[];
  gate_count: number;
  missing_count: number;
  defaulted_count: number;
  owner_groups: {
    owner: "delivery" | "engineering" | "shared";
    gate_count: number;
    missing_count: number;
    defaulted_count: number;
    gates: {
      topic: string;
      setting_name: string;
      status: "answered" | "defaulted" | "missing";
      value_present: boolean;
      required_for: string[];
      notes: string;
      owner: "delivery" | "engineering" | "shared";
    }[];
  }[];
  next_actions: string[];
  public_safety_notes: string[];
};

export type DemoRole = "rep" | "manager" | "admin";

export type DemoIdentity = {
  sub: string;
  role: DemoRole;
  territory_code?: string;
};

export type TerritoryStoreSummary = {
  store_id: string;
  store_name: string;
  rep_id: string;
  priority_score: number;
  oos_sku_count: number;
  confirmed_feedback_count: number;
  false_positive_count: number;
  open_draft_count: number;
  data_freshness_ts: string;
};

export type TerritorySummaryResponse = {
  territory_code: string;
  store_count: number;
  total_oos_alerts: number;
  confirmed_feedback_count: number;
  false_positive_count: number;
  open_draft_count: number;
  stores: TerritoryStoreSummary[];
};

export type ApprovalQueueItem = {
  draft_id: string;
  store_id: string;
  store_name: string;
  rep_id: string;
  session_id: string;
  status: string;
  payload_hash: string;
  item_count: number;
  notes: string | null;
  created_at: string;
};

export type ApprovalQueueResponse = {
  territory_code: string;
  pending_count: number;
  items: ApprovalQueueItem[];
};

export type ManagerTask = {
  task_id: string;
  territory_code: string;
  store_id: string;
  store_name: string | null;
  assigned_rep_id: string;
  created_by: string;
  session_id: string;
  title: string;
  task_type: "shelf_check" | "follow_up" | "promo_check" | "order_review";
  priority: "low" | "medium" | "high";
  due_date: string | null;
  status: "OPEN" | "COMPLETED" | "BLOCKED" | "CANCELLED";
  payload_json: {
    notes?: string | null;
    linked_alert_ids?: string[];
    status_notes?: string | null;
    status_updated_by?: string;
    previous_status?: string;
  };
  created_at: string;
  audit_event_id: string | null;
};

export type ManagerTaskListResponse = {
  territory_code?: string | null;
  assigned_rep_id?: string | null;
  tasks: ManagerTask[];
};

export type AuditEvent = {
  event_id: string;
  session_id: string;
  rep_id: string;
  event_type: string;
  resource_type: string;
  resource_id: string | null;
  payload_json: Record<string, unknown>;
  source_system: string;
  data_freshness_ts: string | null;
  created_at: string;
};

export type AdminAuditEventsResponse = {
  events: AuditEvent[];
  limit: number;
  next_cursor: string | null;
};

export type AdminAuditEventDetailResponse = {
  event: AuditEvent;
};
