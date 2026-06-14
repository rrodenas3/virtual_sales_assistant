from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FeedbackValue = Literal["confirmed", "false_positive", "dismissed", "needs_follow_up"]
ConfidenceLabel = Literal["low", "medium", "high"]


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class PageInfo(BaseModel):
    next_cursor: str | None = None
    limit: int


class VisitComponents(BaseModel):
    oos_risk: float
    promo_gap: float
    revenue_opportunity: float
    visit_recency: float


class VisitPriority(BaseModel):
    store_id: str
    store_name: str
    address: str
    priority_score: float
    rank: int
    reasons: list[str]
    components: VisitComponents
    oos_sku_count: int
    data_freshness_ts: datetime
    audit_event_ids: list[str] = Field(default_factory=list)


class StoreDetail(BaseModel):
    store_id: str
    store_name: str
    retailer_name: str
    address: str
    store_tier: Literal["A", "B", "C"]
    territory_code: str
    rep_id: str
    last_visit_date: str | None
    next_visit_date: str | None
    units_sold_30d: int
    revenue_30d: float
    promo_compliance_rate: float
    revenue_opportunity_score: float
    oos_sku_count: int
    data_freshness_ts: datetime
    audit_event_id: str | None = None


class OOSAlert(BaseModel):
    alert_id: str
    prediction_row_id: str
    store_id: str
    sku_id: str
    sku_name: str
    category: str
    risk_score: float
    is_phantom_inventory: bool
    predicted_stockout_date: str | None
    root_cause_label: str
    recommended_action: str
    confidence_label: ConfidenceLabel
    data_freshness_ts: datetime
    model_version: str
    source_system: str
    audit_event_id: str | None = None


class OOSAlertPage(BaseModel):
    alerts: list[OOSAlert]
    page: PageInfo


class AlertFeedbackRequest(BaseModel):
    feedback: FeedbackValue
    notes: str | None = Field(default=None, max_length=1000)
    session_id: str


class AlertFeedbackResponse(BaseModel):
    id: str
    alert_id: str
    store_id: str
    sku_id: str
    rep_id: str
    feedback: FeedbackValue
    notes: str | None
    session_id: str
    created_at: datetime
    audit_event_id: str


class OSASummaryRequest(BaseModel):
    territory_code: str
    store_id: str | None = None
    session_id: str
    alert_ids: list[str] | None = None


class OSASummaryResponse(BaseModel):
    summary: str
    grounded_alert_ids: list[str]
    session_id: str
    model_id: str
    audit_event_id: str


class AuditEventOut(BaseModel):
    event_id: str
    session_id: str
    rep_id: str
    event_type: str
    resource_type: str
    resource_id: str | None
    payload_json: dict
    source_system: str
    data_freshness_ts: datetime | None
    created_at: datetime


class AuditSessionResponse(BaseModel):
    session_id: str
    events: list[AuditEventOut]
    feedback: list[AlertFeedbackResponse]


class TracePayload(BaseModel):
    session_id: str
    formula_version: str = "priority-v1"
    source_system: str
    model_version: str
    audit_event_ids: list[str]


class PromoRecommendation(BaseModel):
    recommendation_id: str
    store_id: str
    sku_id: str
    promo_name: str
    expected_lift: float
    margin_impact: float
    reason: str
    confidence_label: ConfidenceLabel


class AssortmentGap(BaseModel):
    gap_id: str
    store_id: str
    sku_id: str
    sku_name: str
    category: str
    estimated_revenue_opportunity: float
    reason: str
    confidence_label: ConfidenceLabel


class UpsellOpportunity(BaseModel):
    opportunity_id: str
    store_id: str
    sku_id: str
    sku_name: str
    estimated_value: float
    reason: str
    confidence_label: ConfidenceLabel


class RGMRecommendationsResponse(BaseModel):
    store_id: str
    promos: list[PromoRecommendation]
    assortment_gaps: list[AssortmentGap]
    upsell_opportunities: list[UpsellOpportunity]
    source_system: str = "mock"
    model_version: str = "mock-rgm-v1"
    audit_event_id: str


class OrderDraftItem(BaseModel):
    sku_id: str
    sku_name: str
    quantity: int = Field(ge=1, le=10000)
    reason: str


class CreateOrderDraftRequest(BaseModel):
    store_id: str
    session_id: str
    items: list[OrderDraftItem] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class OrderDraftResponse(BaseModel):
    draft_id: str
    store_id: str
    rep_id: str
    session_id: str
    payload_json: dict
    payload_hash: str
    status: str
    created_at: datetime
    audit_event_id: str | None = None


class ApprovalRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class ApprovalResponse(BaseModel):
    approval_id: str
    draft_id: str
    approved: bool
    approved_by: str
    notes: str | None
    draft_payload_hash: str
    created_at: datetime
    audit_event_id: str


class SandboxSubmitResponse(BaseModel):
    draft_id: str
    status: str
    erp_order_id: str
    submitted_at: datetime
    approval_id: str
    payload_hash: str
    audit_event_id: str


class VisitLogDraftRequest(BaseModel):
    store_id: str
    session_id: str
    notes: str = Field(max_length=2000)
    outcome: Literal["completed", "needs_follow_up", "skipped"]


class VisitLogDraftResponse(BaseModel):
    id: str
    store_id: str
    rep_id: str
    session_id: str
    payload_json: dict
    status: str
    created_at: datetime
    audit_event_id: str


class OfflineFeedbackEvent(BaseModel):
    idempotency_key: str
    alert_id: str
    feedback: FeedbackValue
    session_id: str
    notes: str | None = Field(default=None, max_length=1000)


class OfflineFeedbackSyncRequest(BaseModel):
    events: list[OfflineFeedbackEvent] = Field(min_length=1, max_length=100)


class OfflineFeedbackSyncItem(BaseModel):
    idempotency_key: str
    status: Literal["created", "duplicate"]
    feedback: AlertFeedbackResponse


class OfflineFeedbackSyncResponse(BaseModel):
    results: list[OfflineFeedbackSyncItem]


class PilotMetric(BaseModel):
    name: str
    value: float
    unit: str


class PilotMetricsResponse(BaseModel):
    feedback_count: int
    confirmed_count: int
    false_positive_count: int
    alert_precision: float | None
    summary_count: int
    avg_estimated_cost_eur: float | None
    trace_event_counts: dict[str, int]
    metrics: list[PilotMetric]


class TerritoryStoreSummary(BaseModel):
    store_id: str
    store_name: str
    rep_id: str
    priority_score: float
    oos_sku_count: int
    confirmed_feedback_count: int
    false_positive_count: int
    open_draft_count: int
    data_freshness_ts: datetime


class TerritorySummaryResponse(BaseModel):
    territory_code: str
    store_count: int
    total_oos_alerts: int
    confirmed_feedback_count: int
    false_positive_count: int
    open_draft_count: int
    stores: list[TerritoryStoreSummary]


class AdminAuditEventsResponse(BaseModel):
    events: list[AuditEventOut]
    limit: int
    next_cursor: str | None = None


class AdminAuditEventDetailResponse(BaseModel):
    event: AuditEventOut


class ApprovalQueueItem(BaseModel):
    draft_id: str
    store_id: str
    store_name: str
    rep_id: str
    session_id: str
    status: str
    payload_hash: str
    item_count: int
    notes: str | None
    created_at: datetime


class ApprovalQueueResponse(BaseModel):
    territory_code: str
    pending_count: int
    items: list[ApprovalQueueItem]
