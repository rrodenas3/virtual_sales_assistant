import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Database, MapPin, PackageCheck, Route, ShieldCheck, Tag } from "lucide-react";
import {
  approveOrderDraft,
  createOrderDraft,
  getAlerts,
  getAdminAuditEvents,
  getRGMRecommendations,
  getPilotMetrics,
  getStore,
  getSummary,
  getTerritorySummary,
  getTodayVisits,
  sendFeedback,
  syncFeedbackEvents,
  submitOrderDraftSandbox
} from "./lib/api";
import { getDemoRole, setDemoRole } from "./lib/api";
import { clearQueuedFeedback, getQueuedFeedback, queueFeedback } from "./lib/offlineQueue";
import type {
  AlertFeedback,
  AdminAuditEventsResponse,
  ApprovalResponse,
  DemoRole,
  OOSAlert,
  OrderDraftResponse,
  OSASummaryResponse,
  RGMRecommendationsResponse,
  SandboxSubmitResponse,
  StoreDetail,
  TerritorySummaryResponse,
  VisitPriority
} from "./lib/types";
import { TraceDrawer } from "./components/TraceDrawer";

const sessionId = `REP-001:${new Date().toISOString().slice(0, 10)}:workbench`;

export function App() {
  const [visits, setVisits] = useState<VisitPriority[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [store, setStore] = useState<StoreDetail | null>(null);
  const [alerts, setAlerts] = useState<OOSAlert[]>([]);
  const [rgm, setRgm] = useState<RGMRecommendationsResponse | null>(null);
  const [summary, setSummary] = useState<OSASummaryResponse | null>(null);
  const [draft, setDraft] = useState<OrderDraftResponse | null>(null);
  const [approval, setApproval] = useState<ApprovalResponse | null>(null);
  const [submission, setSubmission] = useState<SandboxSubmitResponse | null>(null);
  const [feedback, setFeedback] = useState<Record<string, AlertFeedback>>({});
  const [queuedCount, setQueuedCount] = useState(0);
  const [online, setOnline] = useState(navigator.onLine);
  const [pilotMetricLabel, setPilotMetricLabel] = useState("No pilot metrics yet");
  const [traceOpen, setTraceOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [role, setRole] = useState<DemoRole>(getDemoRole());
  const [territorySummary, setTerritorySummary] = useState<TerritorySummaryResponse | null>(null);
  const [adminAudit, setAdminAudit] = useState<AdminAuditEventsResponse | null>(null);

  useEffect(() => {
    if (role !== "rep") return;
    getTodayVisits()
      .then((rows) => {
        setVisits(rows);
        setSelectedStoreId(rows[0]?.store_id ?? null);
      })
      .catch((err: Error) => setError(err.message));
  }, [role]);

  useEffect(() => {
    setQueuedCount(getQueuedFeedback().length);
    getPilotMetrics()
      .then((metrics) => {
        const precision = metrics.alert_precision === null ? "n/a" : `${Math.round(metrics.alert_precision * 100)}%`;
        setPilotMetricLabel(`${metrics.feedback_count} feedback / precision ${precision}`);
      })
      .catch(() => setPilotMetricLabel("Metrics unavailable"));

    async function flushQueue() {
      setOnline(navigator.onLine);
      const queued = getQueuedFeedback();
      if (!navigator.onLine || queued.length === 0) return;
      await syncFeedbackEvents(queued);
      clearQueuedFeedback();
      setQueuedCount(0);
    }

    function markOffline() {
      setOnline(false);
    }

    window.addEventListener("online", flushQueue);
    window.addEventListener("offline", markOffline);
    void flushQueue();
    return () => {
      window.removeEventListener("online", flushQueue);
      window.removeEventListener("offline", markOffline);
    };
  }, [role]);

  useEffect(() => {
    if (role !== "rep" || !selectedStoreId) return;
    setSummary(null);
    setDraft(null);
    setApproval(null);
    setSubmission(null);
    Promise.all([getStore(selectedStoreId), getAlerts(selectedStoreId), getRGMRecommendations(selectedStoreId)])
      .then(([storeRow, alertRows, rgmRows]) => {
        setStore(storeRow);
        setAlerts(alertRows);
        setRgm(rgmRows);
      })
      .catch((err: Error) => setError(err.message));
  }, [selectedStoreId, role]);

  useEffect(() => {
    if (role !== "manager") return;
    getTerritorySummary()
      .then(setTerritorySummary)
      .catch((err: Error) => setError(err.message));
  }, [role]);

  useEffect(() => {
    if (role !== "admin") return;
    getAdminAuditEvents()
      .then(setAdminAudit)
      .catch((err: Error) => setError(err.message));
  }, [role]);

  const selectedVisit = useMemo(
    () => visits.find((visit) => visit.store_id === selectedStoreId) ?? null,
    [selectedStoreId, visits]
  );

  async function handleFeedback(alertId: string, value: AlertFeedback) {
    setFeedback((current) => ({ ...current, [alertId]: value }));
    if (!navigator.onLine) {
      setQueuedCount(queueFeedback(alertId, value, sessionId));
      setOnline(false);
      return;
    }
    try {
      await sendFeedback(alertId, value, sessionId);
    } catch (err) {
      setQueuedCount(queueFeedback(alertId, value, sessionId));
      setError(err instanceof Error ? `Feedback queued: ${err.message}` : "Feedback queued");
    }
  }

  async function summarize() {
    if (!selectedStoreId) return;
    const result = await getSummary(selectedStoreId, sessionId, alerts.map((alert) => alert.alert_id));
    setSummary(result);
  }

  async function draftTopAlert() {
    if (!alerts[0]) return;
    const result = await createOrderDraft(alerts[0], sessionId);
    setDraft(result);
    setApproval(null);
  }

  async function approveDraft() {
    if (!draft) return;
    const result = await approveOrderDraft(draft.draft_id);
    setApproval(result);
    setDraft((current) => current ? { ...current, status: "APPROVED" } : current);
  }

  async function submitSandbox() {
    if (!draft) return;
    const result = await submitOrderDraftSandbox(draft.draft_id);
    setSubmission(result);
    setDraft((current) => current ? { ...current, status: result.status } : current);
  }

  function switchRole(nextRole: DemoRole) {
    setDemoRole(nextRole);
    setRole(nextRole);
    setError(null);
    setTerritorySummary(null);
    setAdminAudit(null);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PHANTOM / WEST-01 / {role === "rep" ? "REP-001" : role === "manager" ? "MGR-001" : "ADMIN-001"}</p>
          <h1>{role === "rep" ? "Today's field workbench" : role === "manager" ? "Territory command view" : "Governance audit view"}</h1>
        </div>
        <div className="topbar__actions">
          <div className="roleSwitch">
            {(["rep", "manager", "admin"] as DemoRole[]).map((item) => (
              <button key={item} className={role === item ? "roleSwitch__item roleSwitch__item--active" : "roleSwitch__item"} onClick={() => switchRole(item)}>
                {item}
              </button>
            ))}
          </div>
          <button className="secondaryButton" onClick={() => setTraceOpen(true)}>
            <Database size={16} /> Trace
          </button>
          <div className="statusPill"><ShieldCheck size={16} /> Mock JWT active</div>
          <div className={online ? "statusPill" : "statusPill statusPill--offline"}>
            {online ? "Online" : "Offline"} / queued {queuedCount}
          </div>
          <div className="statusPill">{pilotMetricLabel}</div>
        </div>
      </header>

      {error && <div className="errorBanner">{error}</div>}

      {role === "manager" && territorySummary && (
        <section className="leadershipPane">
          <div className="metricStrip">
            <div><span>Stores</span><strong>{territorySummary.store_count}</strong></div>
            <div><span>OOS alerts</span><strong>{territorySummary.total_oos_alerts}</strong></div>
            <div><span>Confirmed</span><strong>{territorySummary.confirmed_feedback_count}</strong></div>
            <div><span>Open drafts</span><strong>{territorySummary.open_draft_count}</strong></div>
          </div>
          <div className="managerTable">
            {territorySummary.stores.map((row) => (
              <button key={row.store_id} className="managerRow" onClick={() => { switchRole("rep"); setSelectedStoreId(row.store_id); }}>
                <strong>{row.store_name}</strong>
                <span>{row.rep_id}</span>
                <span>priority {row.priority_score.toFixed(3)}</span>
                <span>{row.oos_sku_count} OOS</span>
                <span>{row.confirmed_feedback_count} confirmed</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {role === "admin" && adminAudit && (
        <section className="leadershipPane">
          <div className="sectionHead">
            <div>
              <p className="eyebrow">Audit</p>
              <h3>{adminAudit.events.length} recent events</h3>
            </div>
          </div>
          <div className="auditFeed">
            {adminAudit.events.map((event) => (
              <article key={event.event_id} className="auditRow">
                <strong>{event.event_type}</strong>
                <span>{event.rep_id} / {event.resource_type} / {event.resource_id ?? "none"}</span>
                <span>{new Date(event.created_at).toLocaleString()}</span>
              </article>
            ))}
          </div>
        </section>
      )}

      {role === "rep" && (
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
                className={`visitRow ${visit.store_id === selectedStoreId ? "visitRow--active" : ""}`}
                onClick={() => setSelectedStoreId(visit.store_id)}
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
                    <button className="primaryButton" onClick={draftTopAlert} disabled={!alerts[0]}>
                      Draft top alert
                    </button>
                    {draft && (
                      <div className="draftStatus">
                        <strong>Draft {draft.status}</strong>
                        <span>{draft.draft_id.slice(0, 8)} / hash {draft.payload_hash.slice(0, 10)}</span>
                        {draft.status === "DRAFT" && <button className="secondaryButton" onClick={approveDraft}>Approve</button>}
                        {draft.status === "APPROVED" && <button className="secondaryButton" onClick={submitSandbox}>Submit sandbox</button>}
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
                  <h3>{alerts.length} grounded shelf risks</h3>
                </div>
                <button className="primaryButton" onClick={summarize}>Generate summary</button>
              </div>

              {summary && <pre className="summaryBox">{summary.summary}</pre>}

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
                          className={feedback[alert.alert_id] === value ? "feedbackButton feedbackButton--active" : "feedbackButton"}
                          onClick={() => handleFeedback(alert.alert_id, value)}
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
      )}

      <TraceDrawer
        open={traceOpen}
        onClose={() => setTraceOpen(false)}
        selectedVisit={selectedVisit}
        store={store}
        alerts={alerts}
        summaryAuditId={summary?.audit_event_id ?? null}
      />
    </main>
  );
}
