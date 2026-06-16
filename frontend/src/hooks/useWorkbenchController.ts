import { useEffect, useMemo, useState } from "react";

import {
  AGENT_RUN_ENABLED,
  approveOrderDraft,
  buildSessionId,
  createManagerTask,
  createOrderDraft,
  getActivationRunbook,
  getAdminAuditEvent,
  getAdminAuditEvents,
  getAlerts,
  getApprovalQueue,
  getCurrentIdentity,
  getDemoRole,
  getDiscoveryPacket,
  getIntegrationReadiness,
  getManagerTasks,
  getMyManagerTasks,
  getPilotGapReport,
  getPilotMetrics,
  getRGMRecommendations,
  getStore,
  getSummary,
  getTerritorySummary,
  getTodayVisits,
  runAgentSummary,
  sendFeedback,
  setDemoRole,
  submitOrderDraftSandbox,
  syncFeedbackEvents,
  updateManagerTaskStatus
} from "../lib/api";
import { cacheGet, cacheKey, cacheSet } from "../lib/offlineCache";
import { clearQueuedFeedback, getQueuedFeedback, queueFeedback } from "../lib/offlineQueue";
import type {
  AlertFeedback,
  ActivationRunbook,
  AdminAuditEventDetailResponse,
  AdminAuditEventsResponse,
  AgentRunEvent,
  ApprovalQueueResponse,
  ApprovalResponse,
  DemoRole,
  DiscoveryPacket,
  IntegrationReadinessResponse,
  ManagerTask,
  ManagerTaskListResponse,
  OOSAlert,
  PilotGapReport,
  OrderDraftResponse,
  OSASummaryResponse,
  RGMRecommendationsResponse,
  SandboxSubmitResponse,
  StoreDetail,
  TerritoryStoreSummary,
  TerritorySummaryResponse,
  VisitPriority
} from "../lib/types";

export type AuditFilters = {
  event_type: string;
  rep_id: string;
  resource_type: string;
};

export function useWorkbenchController() {
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
  const [pilotGapReport, setPilotGapReport] = useState<PilotGapReport | null>(null);
  const [activationRunbook, setActivationRunbook] = useState<ActivationRunbook | null>(null);
  const [discoveryPacket, setDiscoveryPacket] = useState<DiscoveryPacket | null>(null);
  const [managerTasks, setManagerTasks] = useState<ManagerTaskListResponse | null>(null);
  const [myTasks, setMyTasks] = useState<ManagerTaskListResponse | null>(null);
  const [taskNotice, setTaskNotice] = useState<string | null>(null);
  const [adminAudit, setAdminAudit] = useState<AdminAuditEventsResponse | null>(null);
  const [auditDetail, setAuditDetail] = useState<AdminAuditEventDetailResponse | null>(null);
  const [auditFilters, setAuditFilters] = useState<AuditFilters>({ event_type: "", rep_id: "", resource_type: "" });
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
    Promise.all([getIntegrationReadiness(), getPilotGapReport("pilot"), getActivationRunbook("pilot"), getDiscoveryPacket("pilot")])
      .then(([readinessRows, gapRows, runbookRows, discoveryRows]) => {
        setReadiness(readinessRows);
        setPilotGapReport(gapRows);
        setActivationRunbook(runbookRows);
        setDiscoveryPacket(discoveryRows);
      })
      .catch(() => {
        setReadiness(null);
        setPilotGapReport(null);
        setActivationRunbook(null);
        setDiscoveryPacket(null);
      });
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
    setApprovalQueue(await getApprovalQueue());
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
    setAuditDetail(await getAdminAuditEvent(eventId));
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
    setPilotGapReport(null);
    setActivationRunbook(null);
    setDiscoveryPacket(null);
    setManagerTasks(null);
    setMyTasks(null);
    setTaskNotice(null);
    setAdminAudit(null);
    setAuditDetail(null);
  }

  function openManagerStore(row: TerritoryStoreSummary) {
    switchRole("rep");
    setSelectedStoreId(row.store_id);
  }

  return {
    agentRunEnabled: AGENT_RUN_ENABLED,
    identity,
    role,
    online,
    queuedCount,
    pilotMetricLabel,
    traceOpen,
    error,
    cacheNotice,
    taskNotice,
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
    territorySummary,
    approvalQueue,
    readiness,
    pilotGapReport,
    activationRunbook,
    discoveryPacket,
    managerTasks,
    myTasks,
    adminAudit,
    auditDetail,
    auditFilters,
    setTraceOpen,
    setSelectedStoreId,
    setAuditFilters,
    switchRole,
    openManagerStore,
    assignShelfCheck,
    changeTaskStatus,
    approveQueueDraft,
    openAuditDetail,
    draftTopAlert,
    approveDraft,
    submitSandbox,
    runAssistant,
    summarize,
    handleFeedback
  };
}
