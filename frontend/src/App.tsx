import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, Clock, Database, MapPin, PackageCheck, Route, ShieldCheck, Tag } from "lucide-react";
import {
  AGENT_RUN_ENABLED,
  approveOrderDraft,
  createManagerTask,
  createOrderDraft,
  getAdminAuditEvent,
  getAlerts,
  getAdminAuditEvents,
  getApprovalQueue,
  getIntegrationReadiness,
  getManagerTasks,
  getMyManagerTasks,
  getRGMRecommendations,
  getPilotMetrics,
  getStore,
  getSummary,
  getTerritorySummary,
  getTodayVisits,
  sendFeedback,
  runAgentSummary,
  syncFeedbackEvents,
  submitOrderDraftSandbox,
  updateManagerTaskStatus
} from "./lib/api";
import { buildSessionId, getCurrentIdentity, getDemoRole, setDemoRole } from "./lib/api";
import { clearQueuedFeedback, getQueuedFeedback, queueFeedback } from "./lib/offlineQueue";
import { cacheGet, cacheKey, cacheSet } from "./lib/offlineCache";
import type {
  AlertFeedback,
  AdminAuditEventDetailResponse,
  AdminAuditEventsResponse,
  AgentRunEvent,
  ApprovalResponse,
  ApprovalQueueResponse,
  DemoRole,
  IntegrationReadinessResponse,
  ManagerTask,
  ManagerTaskListResponse,
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
import { ReadinessPanel } from "./components/ReadinessPanel";

export function App() {
  const [visits, setVisits] = useState<VisitPriority[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [store, setStore] = useState<StoreDetail | null>(null);
  const [alerts, setAlerts] = useState<OOSAlert[]>([]);
  const [rgm, setRgm] = useState<RGMRecommendationsResponse | null>(null);
  const [summary, setSummary] = useState<OSASummaryResponse | null>(null);
  const [agentEvents, setAgentEvents] = useState<AgentRunEvent[]>([]);
  const [agentRunning, setAgentRunning] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [draft, setDraft] = useState<OrderDraftResponse | null>(null);
  const [approval, setApproval] = useState<ApprovalResponse | null>(null);
  const [submission, setSubmission] = useState<SandboxSubmitResponse | null>(null);
  const [feedback, setFeedback] = useState<Record<string, AlertFeedback>>({});
  const [queuedCount, setQueuedCount] = useState(0);
  const [online, setOnline] = useState(navigator.onLine);
  const [pilotMetricLabel, setPilotMetricLabel] = useState("No pilot metrics yet");
  const [traceOpen, setTraceOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheNotice, setCacheNotice] = useState<string | null>(null);
  const [role, setRole] = useState<DemoRole>(getDemoRole());
  const [territorySummary, setTerritorySummary] = useState<TerritorySummaryResponse | null>(null);
  const [approvalQueue, setApprovalQueue] = useState<ApprovalQueueResponse | null>(null);
  const [readiness, setReadiness] = useState<IntegrationReadinessResponse | null>(null);
  const [managerTasks, setManagerTasks] = useState<ManagerTaskListResponse | null>(null);
  const [myTasks, setMyTasks] = useState<ManagerTaskListResponse | null>(null);
  const [taskNotice, setTaskNotice] = useState<string | null>(null);
  const [adminAudit, setAdminAudit] = useState<AdminAuditEventsResponse | null>(null);
  const [auditDetail, setAuditDetail] = useState<AdminAuditEventDetailResponse | null>(null);
  const [auditFilters, setAuditFilters] = useState({ event_type: "", rep_id: "", resource_type: "" });
  const identity = useMemo(() => getCurrentIdentity(), [role]);
  const sessionId = useMemo(() => buildSessionId("workbench"), [identity.sub]);

  useEffect(() => {
    if (role !== "rep") return;
    const key = cacheKey(identity.sub, "today-route");
    getTodayVisits()
      .then(async (rows) => {
        setVisits(rows);
        setSelectedStoreId(rows[0]?.store_id ?? null);
        setCacheNotice(null);
        await cacheSet(key, rows);
      })
      .catch(async (err: Error) => {
        const cached = await cacheGet<VisitPriority[]>(key);
        if (cached) {
          setVisits(cached.value);
          setSelectedStoreId(cached.value[0]?.store_id ?? null);
          setCacheNotice(`Route cache from ${new Date(cached.cached_at).toLocaleString()}`);
          setOnline(false);
          return;
        }
        setError(err.message);
      });
  }, [role, identity.sub]);

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
    setAgentEvents([]);
    setAgentError(null);
    setDraft(null);
    setApproval(null);
    setSubmission(null);
    const storeKey = cacheKey(identity.sub, "store", selectedStoreId);
    const alertsKey = cacheKey(identity.sub, "alerts", selectedStoreId);
    const rgmKey = cacheKey(identity.sub, "rgm", selectedStoreId);
    Promise.all([getStore(selectedStoreId), getAlerts(selectedStoreId), getRGMRecommendations(selectedStoreId)])
      .then(async ([storeRow, alertRows, rgmRows]) => {
        setStore(storeRow);
        setAlerts(alertRows);
        setRgm(rgmRows);
        setCacheNotice(null);
        await Promise.all([cacheSet(storeKey, storeRow), cacheSet(alertsKey, alertRows), cacheSet(rgmKey, rgmRows)]);
      })
      .catch(async (err: Error) => {
        const [cachedStore, cachedAlerts, cachedRgm] = await Promise.all([
          cacheGet<StoreDetail>(storeKey),
          cacheGet<OOSAlert[]>(alertsKey),
          cacheGet<RGMRecommendationsResponse>(rgmKey)
        ]);
        if (cachedStore && cachedAlerts && cachedRgm) {
          setStore(cachedStore.value);
          setAlerts(cachedAlerts.value);
          setRgm(cachedRgm.value);
          setCacheNotice(`Store cache from ${new Date(cachedStore.cached_at).toLocaleString()}`);
          setOnline(false);
          return;
        }
        setError(err.message);
      });
  }, [selectedStoreId, role, identity.sub]);

  useEffect(() => {
    if (role !== "manager" && role !== "admin") return;
    getIntegrationReadiness()
      .then(setReadiness)
      .catch(() => setReadiness(null));
  }, [role]);

  useEffect(() => {
    if (role !== "manager") return;
    Promise.all([getTerritorySummary(), getApprovalQueue(), getManagerTasks()])
      .then(([summaryRows, queueRows, taskRows]) => {
        setTerritorySummary(summaryRows);
        setApprovalQueue(queueRows);
        setManagerTasks(taskRows);
      })
      .catch((err: Error) => setError(err.message));
  }, [role]);

  useEffect(() => {
    if (role !== "rep") return;
    getMyManagerTasks("OPEN")
      .then(setMyTasks)
      .catch(() => setMyTasks(null));
  }, [role]);

  useEffect(() => {
    if (role !== "admin") return;
    getAdminAuditEvents(auditFilters)
      .then(setAdminAudit)
      .catch((err: Error) => setError(err.message));
  }, [role, auditFilters]);

  const selectedVisit = useMemo(
    () => visits.find((visit) => visit.store_id === selectedStoreId) ?? null,
    [selectedStoreId, visits]
  );
  const openMyTasks = useMemo(() => {
    const seen = new Set<string>();
    return (myTasks?.tasks ?? []).filter((task) => {
      if (task.status !== "OPEN") return false;
      const taskKey = `${task.store_id}:${task.task_type}:${task.title}`;
      if (seen.has(taskKey)) return false;
      seen.add(taskKey);
      return true;
    });
  }, [myTasks]);

  async function handleFeedback(alertId: string, value: AlertFeedback) {
    setFeedback((current) => ({ ...current, [alertId]: value }));
    if (!navigator.onLine) {
      setQueuedCount(queueFeedback(alertId, value, sessionId, identity.sub));
      setOnline(false);
      return;
    }
    try {
      await sendFeedback(alertId, value, sessionId);
    } catch (err) {
      setQueuedCount(queueFeedback(alertId, value, sessionId, identity.sub));
      setError(err instanceof Error ? `Feedback queued: ${err.message}` : "Feedback queued");
    }
  }

  async function summarize() {
    if (!selectedStoreId) return;
    const result = await getSummary(selectedStoreId, sessionId, alerts.map((alert) => alert.alert_id));
    setSummary(result);
  }

  async function runAssistant() {
    if (!selectedStoreId || !AGENT_RUN_ENABLED) return;
    setAgentEvents([]);
    setAgentError(null);
    setAgentRunning(true);
    try {
      await runAgentSummary(selectedStoreId, sessionId, alerts.map((alert) => alert.alert_id), (event) => {
        setAgentEvents((current) => [...current, event]);
        if (event.event === "message") {
          setSummary({
            summary: event.data.content,
            grounded_alert_ids: event.data.grounded_alert_ids,
            session_id: sessionId,
            model_id: "",
            audit_event_id: ""
          });
        }
        if (event.event === "audit") {
          setSummary((current) =>
            current
              ? {
                  ...current,
                  audit_event_id: event.data.audit_event_id,
                  model_id: event.data.model_id
                }
              : current
          );
        }
      });
    } catch (err) {
      setAgentError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setAgentRunning(false);
    }
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

  async function approveQueueDraft(draftId: string) {
    await approveOrderDraft(draftId);
    const queueRows = await getApprovalQueue();
    setApprovalQueue(queueRows);
  }

  async function assignShelfCheck(row: { store_id: string; store_name: string; rep_id: string }) {
    const created = await createManagerTask({
      store_id: row.store_id,
      assigned_rep_id: row.rep_id,
      session_id: buildSessionId("manager_work"),
      title: `Verify shelf at ${row.store_name}`,
      task_type: "shelf_check",
      priority: "medium",
      notes: "Confirm top OOS risks before the next replenishment decision."
    });
    setTaskNotice(`Assigned ${created.title}`);
    setManagerTasks(await getManagerTasks());
  }

  async function changeTaskStatus(task: ManagerTask, status: "COMPLETED" | "BLOCKED" | "CANCELLED") {
    const updated = await updateManagerTaskStatus(task.task_id, status, buildSessionId("manager_work_status"));
    setTaskNotice(`${updated.title} marked ${updated.status.toLowerCase()}`);
    if (role === "manager") setManagerTasks(await getManagerTasks());
    if (role === "rep") setMyTasks(await getMyManagerTasks("OPEN"));
  }

  async function openAuditDetail(eventId: string) {
    const detail = await getAdminAuditEvent(eventId);
    setAuditDetail(detail);
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
    setApprovalQueue(null);
    setReadiness(null);
    setManagerTasks(null);
    setMyTasks(null);
    setTaskNotice(null);
    setAdminAudit(null);
    setAuditDetail(null);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PHANTOM / {identity.territory_code ?? "all territories"} / {identity.sub}</p>
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
      {cacheNotice && <div className="cacheBanner">{cacheNotice}</div>}
      {taskNotice && <div className="cacheBanner">{taskNotice}</div>}

      {role === "manager" && territorySummary && (
        <section className="leadershipPane">
          {readiness && <ReadinessPanel readiness={readiness} variant="manager" />}
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
          <div className="queueBlock">
            <div className="sectionHead">
              <div>
                <p className="eyebrow">Manager tasks</p>
                <h3>{managerTasks?.tasks.length ?? 0} assigned tasks</h3>
              </div>
            </div>
            <div className="taskQueue">
              {territorySummary.stores.map((row) => (
                <article key={`assign-${row.store_id}`} className="taskRow">
                  <div>
                    <strong>{row.store_name}</strong>
                    <span>{row.rep_id} / {row.oos_sku_count} OOS risks</span>
                  </div>
                  <button className="secondaryButton" data-testid={`assign-work-${row.store_id}`} onClick={() => assignShelfCheck(row)}>
                    Assign shelf check
                  </button>
                </article>
              ))}
              {managerTasks?.tasks.map((task) => (
                <article key={task.task_id} className="taskRow">
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.store_name ?? task.store_id} / {task.assigned_rep_id} / {task.status}</span>
                  </div>
                  <button
                    className="secondaryButton"
                    data-testid={`cancel-work-${task.task_id}`}
                    disabled={task.status === "CANCELLED"}
                    onClick={() => changeTaskStatus(task, "CANCELLED")}
                  >
                    Cancel
                  </button>
                </article>
              ))}
            </div>
          </div>
          {approvalQueue && (
            <div className="queueBlock">
              <div className="sectionHead">
                <div>
                  <p className="eyebrow">Approval queue</p>
                  <h3>{approvalQueue.pending_count} pending drafts</h3>
                </div>
              </div>
              <div className="approvalQueue">
                {approvalQueue.items.map((item) => (
                  <article key={item.draft_id} className="approvalRow">
                    <div>
                      <strong>{item.store_name}</strong>
                      <span>{item.rep_id} / {item.item_count} items / {item.status}</span>
                    </div>
                    <span>hash {item.payload_hash.slice(0, 10)}</span>
                    <button className="secondaryButton" onClick={() => approveQueueDraft(item.draft_id)}>Approve</button>
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {role === "admin" && adminAudit && (
        <section className="leadershipPane">
          {readiness && <ReadinessPanel readiness={readiness} variant="admin" />}
          <div className="sectionHead">
            <div>
              <p className="eyebrow">Audit</p>
              <h3>{adminAudit.events.length} recent events</h3>
            </div>
          </div>
          <div className="filterBar">
            <input placeholder="event type" value={auditFilters.event_type} onChange={(event) => setAuditFilters((current) => ({ ...current, event_type: event.target.value }))} />
            <input placeholder="rep id" value={auditFilters.rep_id} onChange={(event) => setAuditFilters((current) => ({ ...current, rep_id: event.target.value }))} />
            <input placeholder="resource type" value={auditFilters.resource_type} onChange={(event) => setAuditFilters((current) => ({ ...current, resource_type: event.target.value }))} />
          </div>
          <div className="auditFeed">
            {adminAudit.events.map((event) => (
              <button key={event.event_id} className="auditRow" onClick={() => openAuditDetail(event.event_id)}>
                <strong>{event.event_type}</strong>
                <span>{event.rep_id} / {event.resource_type} / {event.resource_id ?? "none"}</span>
                <span>{new Date(event.created_at).toLocaleString()}</span>
              </button>
            ))}
          </div>
          {auditDetail && (
            <pre className="summaryBox auditDetail">{JSON.stringify(auditDetail.event, null, 2)}</pre>
          )}
        </section>
      )}

      {role === "rep" && (
      <>
      {myTasks && openMyTasks.length > 0 && (
        <section className="taskStrip" data-testid="my-tasks">
          <div>
            <p className="eyebrow">Assigned work</p>
            <h3>{openMyTasks.length} open tasks</h3>
          </div>
          <div className="taskQueue">
            {openMyTasks.map((task) => (
              <article key={task.task_id} className="taskRow">
                <div>
                  <strong>{task.title}</strong>
                  <span>{task.store_name ?? task.store_id} / {task.priority} / {task.status}</span>
                </div>
                <div className="taskActions">
                  <button
                    className="secondaryButton"
                    data-testid={`complete-work-${task.task_id}`}
                    disabled={task.status !== "OPEN"}
                    onClick={() => changeTaskStatus(task, "COMPLETED")}
                  >
                    Complete
                  </button>
                  <button
                    className="secondaryButton"
                    disabled={task.status !== "OPEN"}
                    onClick={() => changeTaskStatus(task, "BLOCKED")}
                  >
                    Block
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
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
                  <h3 data-testid="alert-count">{alerts.length} grounded shelf risks</h3>
                </div>
                <div className="sectionActions">
                  {AGENT_RUN_ENABLED && (
                    <button className="primaryButton" data-testid="run-agent" onClick={runAssistant} disabled={agentRunning || alerts.length === 0}>
                      <Bot size={16} /> {agentRunning ? "Running" : "Run agent"}
                    </button>
                  )}
                  <button className="secondaryButton" data-testid="generate-summary" onClick={summarize}>Generate summary</button>
                </div>
              </div>

              {AGENT_RUN_ENABLED && (
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
      </>
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
