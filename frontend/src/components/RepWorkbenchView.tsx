import { AlertTriangle, Bot, CheckCircle2, Clock, MapPin, PackageCheck, Route, Tag } from "lucide-react";

import { AssignedWorkPanel } from "./AssignedWorkPanel";
import type {
  AlertFeedback,
  AgentRunEvent,
  ApprovalResponse,
  ManagerTask,
  ManagerTaskListResponse,
  OOSAlert,
  OrderDraftResponse,
  OSASummaryResponse,
  RGMRecommendationsResponse,
  SandboxSubmitResponse,
  StoreDetail,
  VisitPriority
} from "../lib/types";

export function RepWorkbenchView({
  agentRunEnabled,
  visits,
  selectedStoreId,
  selectedVisit,
  store,
  alerts,
  rgm,
  summary,
  agentEvents,
  agentRunning,
  agentError,
  draft,
  approval,
  submission,
  feedback,
  myTasks,
  onSelectStore,
  onTaskStatusChange,
  onDraftTopAlert,
  onApproveDraft,
  onSubmitSandbox,
  onRunAssistant,
  onSummarize,
  onFeedback
}: {
  agentRunEnabled: boolean;
  visits: VisitPriority[];
  selectedStoreId: string | null;
  selectedVisit: VisitPriority | null;
  store: StoreDetail | null;
  alerts: OOSAlert[];
  rgm: RGMRecommendationsResponse | null;
  summary: OSASummaryResponse | null;
  agentEvents: AgentRunEvent[];
  agentRunning: boolean;
  agentError: string | null;
  draft: OrderDraftResponse | null;
  approval: ApprovalResponse | null;
  submission: SandboxSubmitResponse | null;
  feedback: Record<string, AlertFeedback>;
  myTasks: ManagerTaskListResponse | null;
  onSelectStore: (storeId: string) => void;
  onTaskStatusChange: (task: ManagerTask, status: "COMPLETED" | "BLOCKED") => void;
  onDraftTopAlert: () => void;
  onApproveDraft: () => void;
  onSubmitSandbox: () => void;
  onRunAssistant: () => void;
  onSummarize: () => void;
  onFeedback: (alertId: string, value: AlertFeedback) => void;
}) {
  return (
    <>
      {myTasks && <AssignedWorkPanel tasks={myTasks.tasks} onStatusChange={onTaskStatusChange} />}
      <section className="layout">
        <aside className="routePane">
          <div className="paneTitle">
            <Route size={18} />
            <h2>Priority route</h2>
          </div>
          <div className="visitList">
            {visits.map((visit) => (
              <button
                key={visit.store_id}
                data-testid={`visit-${visit.store_id}`}
                className={`visitRow ${visit.store_id === selectedStoreId ? "visitRow--active" : ""}`}
                onClick={() => onSelectStore(visit.store_id)}
              >
                <span className="rank">{visit.rank}</span>
                <span className="visitMain">
                  <strong>{visit.store_name}</strong>
                  <span>{visit.oos_sku_count} OOS risks / score {visit.priority_score.toFixed(3)}</span>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="detailPane">
          {store && selectedVisit ? (
            <>
              <div className="storeHeader">
                <div>
                  <p className="eyebrow">{store.retailer_name} / Tier {store.store_tier}</p>
                  <h2>{store.store_name}</h2>
                  <p className="address"><MapPin size={15} /> {store.address}</p>
                </div>
                <div className="scoreDial">
                  <span>{selectedVisit.priority_score.toFixed(3)}</span>
                  <small>priority</small>
                </div>
              </div>

              <div className="metricStrip">
                <div><span>30d revenue</span><strong>€{Math.round(store.revenue_30d).toLocaleString()}</strong></div>
                <div><span>Promo compliance</span><strong>{Math.round(store.promo_compliance_rate * 100)}%</strong></div>
                <div><span>Revenue opportunity</span><strong>{Math.round(store.revenue_opportunity_score * 100)}%</strong></div>
                <div><span>Freshness</span><strong>{new Date(store.data_freshness_ts).toLocaleDateString()}</strong></div>
              </div>

              <section className="reasonBand">
                {selectedVisit.reasons.map((reason) => <span key={reason}>{reason}</span>)}
              </section>

              {rgm && (
                <section className="actionBand">
                  <div className="actionBand__item">
                    <Tag size={18} />
                    <div>
                      <span>Promo move</span>
                      <strong>{rgm.promos[0]?.promo_name}</strong>
                      <p>{rgm.promos[0]?.reason}</p>
                    </div>
                  </div>
                  <div className="actionBand__item">
                    <PackageCheck size={18} />
                    <div>
                      <span>Assortment gap</span>
                      <strong>{rgm.assortment_gaps[0]?.sku_name}</strong>
                      <p>€{Math.round(rgm.assortment_gaps[0]?.estimated_revenue_opportunity ?? 0).toLocaleString()} opportunity</p>
                    </div>
                  </div>
                  <div className="draftPanel">
                    <button className="primaryButton" onClick={onDraftTopAlert} disabled={!alerts[0]}>
                      Draft top alert
                    </button>
                    {draft && (
                      <div className="draftStatus">
                        <strong>Draft {draft.status}</strong>
                        <span>{draft.draft_id.slice(0, 8)} / hash {draft.payload_hash.slice(0, 10)}</span>
                        {draft.status === "DRAFT" && <button className="secondaryButton" onClick={onApproveDraft}>Approve</button>}
                        {draft.status === "APPROVED" && <button className="secondaryButton" onClick={onSubmitSandbox}>Submit sandbox</button>}
                        {approval && <span>Approved audit {approval.audit_event_id.slice(0, 8)}</span>}
                        {submission && <span>ERP {submission.erp_order_id}</span>}
                      </div>
                    )}
                  </div>
                </section>
              )}

              <div className="sectionHead">
                <div>
                  <p className="eyebrow">OSA alerts</p>
                  <h3 data-testid="alert-count">{alerts.length} grounded shelf risks</h3>
                </div>
                <div className="sectionActions">
                  {agentRunEnabled && (
                    <button className="primaryButton" data-testid="run-agent" onClick={onRunAssistant} disabled={agentRunning || alerts.length === 0}>
                      <Bot size={16} /> {agentRunning ? "Running" : "Run agent"}
                    </button>
                  )}
                  <button className="secondaryButton" data-testid="generate-summary" onClick={onSummarize}>Generate summary</button>
                </div>
              </div>

              {agentRunEnabled && (
                <section className="agentPanel" data-testid="agent-panel">
                  <div className="agentPanel__top">
                    <div>
                      <p className="eyebrow">Agent stream</p>
                      <h3>Grounded OSA assistant</h3>
                    </div>
                    <span className={agentRunning ? "agentState agentState--running" : "agentState"}>
                      {agentRunning ? "Streaming" : agentEvents.length ? "Ready" : "Idle"}
                    </span>
                  </div>
                  {agentError && <div className="agentError">{agentError}</div>}
                  <div className="agentTimeline">
                    {agentEvents.length === 0 && <p className="agentEmpty">Run the agent to stream a grounded summary and trace event for this store.</p>}
                    {agentEvents.map((event, index) => (
                      <div key={`${event.event}-${index}`} className="agentEvent">
                        <span>{event.event.replace(/_/g, " ")}</span>
                        <strong>
                          {event.event === "message"
                            ? event.data.content
                            : event.event === "audit"
                              ? `${event.data.model_id} / audit ${event.data.audit_event_id.slice(0, 8)}`
                              : event.data.run_id}
                        </strong>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {summary && <pre className="summaryBox" data-testid="summary-box">{summary.summary}</pre>}

              <div className="alertList">
                {alerts.map((alert) => (
                  <article className="alertRow" key={alert.alert_id}>
                    <div className="alertRow__main">
                      <div className="alertIcon"><AlertTriangle size={18} /></div>
                      <div>
                        <div className="alertTitle">
                          <strong>{alert.sku_name}</strong>
                          {alert.is_phantom_inventory && <span className="phantomBadge">Phantom</span>}
                          <span className={`confidence confidence--${alert.confidence_label}`}>{alert.confidence_label}</span>
                        </div>
                        <p>{alert.category} / {alert.root_cause_label} / {Math.round(alert.risk_score * 100)}% risk</p>
                        <p className="actionLine">{alert.recommended_action}</p>
                      </div>
                    </div>
                    <div className="feedbackRail">
                      {(["confirmed", "false_positive", "dismissed", "needs_follow_up"] as AlertFeedback[]).map((value) => (
                        <button
                          key={value}
                          data-testid={`feedback-${alert.alert_id}-${value}`}
                          className={feedback[alert.alert_id] === value ? "feedbackButton feedbackButton--active" : "feedbackButton"}
                          onClick={() => onFeedback(alert.alert_id, value)}
                        >
                          {value === "confirmed" ? <CheckCircle2 size={14} /> : <Clock size={14} />}
                          {value.replace(/_/g, " ")}
                        </button>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <div className="emptyState">Loading route intelligence...</div>
          )}
        </section>
      </section>
    </>
  );
}
