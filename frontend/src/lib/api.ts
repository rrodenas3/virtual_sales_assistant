import type {
  AlertFeedback,
  AdminAuditEventsResponse,
  AdminAuditEventDetailResponse,
  AgentRunEvent,
  ApprovalQueueResponse,
  ApprovalResponse,
  DemoIdentity,
  DemoRole,
  ManagerTask,
  ManagerTaskListResponse,
  OOSAlert,
  OrderDraftResponse,
  OSASummaryResponse,
  OfflineFeedbackEvent,
  PilotMetricsResponse,
  RGMRecommendationsResponse,
  SandboxSubmitResponse,
  StoreDetail,
  TerritorySummaryResponse,
  VisitPriority
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const AGENT_RUN_ENABLED = import.meta.env.VITE_AGENT_RUN_ENABLED !== "false";
const ROLE_KEY = "phantom.demoRole";
const DEFAULT_TERRITORY = "WEST-01";

function encodeSegment(value: unknown) {
  return btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function mockTokenForRole(role: DemoRole) {
  const claims =
    role === "rep"
      ? { sub: "REP-001", territory_code: "WEST-01", role }
      : role === "manager"
        ? { sub: "MGR-001", territory_code: "WEST-01", role }
        : { sub: "ADMIN-001", role };
  return `${encodeSegment({ alg: "none", typ: "JWT" })}.${encodeSegment(claims)}.`;
}

function decodeSegment<T>(segment: string): T {
  const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  return JSON.parse(atob(padded)) as T;
}

export function getDemoRole(): DemoRole {
  const role = window.localStorage.getItem(ROLE_KEY);
  return role === "manager" || role === "admin" ? role : "rep";
}

export function setDemoRole(role: DemoRole) {
  window.localStorage.setItem(ROLE_KEY, role);
}

export function getCurrentIdentity(): DemoIdentity {
  const token = mockTokenForRole(getDemoRole());
  return decodeSegment<DemoIdentity>(token.split(".")[1]);
}

export function getCurrentTerritory(): string {
  return getCurrentIdentity().territory_code ?? DEFAULT_TERRITORY;
}

export function buildSessionId(scope = "workbench", date = new Date()): string {
  return `${getCurrentIdentity().sub}:${date.toISOString().slice(0, 10)}:${scope}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${mockTokenForRole(getDemoRole())}`,
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(body.message ?? body.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export function getTodayVisits(): Promise<VisitPriority[]> {
  const today = new Date().toISOString().slice(0, 10);
  return request(`/api/v1/visits/today?territory_code=${encodeURIComponent(getCurrentTerritory())}&date=${today}`);
}

export function getStore(storeId: string): Promise<StoreDetail> {
  return request(`/api/v1/stores/${storeId}`);
}

export async function getAlerts(storeId: string): Promise<OOSAlert[]> {
  const page = await request<{ alerts: OOSAlert[] }>(`/api/v1/stores/${storeId}/alerts?limit=50`);
  return page.alerts;
}

export function sendFeedback(alertId: string, feedback: AlertFeedback, sessionId: string): Promise<unknown> {
  return request(`/api/v1/alerts/${encodeURIComponent(alertId)}/feedback`, {
    method: "POST",
    body: JSON.stringify({ feedback, session_id: sessionId })
  });
}

export function getSummary(storeId: string, sessionId: string, alertIds: string[]): Promise<OSASummaryResponse> {
  return request("/api/v1/agent/osa-summary", {
    method: "POST",
    body: JSON.stringify({
      territory_code: getCurrentTerritory(),
      store_id: storeId,
      session_id: sessionId,
      alert_ids: alertIds
    })
  });
}

export async function runAgentSummary(
  storeId: string,
  sessionId: string,
  alertIds: string[],
  onEvent: (event: AgentRunEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/agent/run`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${mockTokenForRole(getDemoRole())}`
    },
    body: JSON.stringify({
      intent: "osa_summary",
      territory_code: getCurrentTerritory(),
      store_id: storeId,
      session_id: sessionId,
      alert_ids: alertIds
    })
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(body.message ?? body.detail ?? "Agent run failed");
  }
  if (!response.body) throw new Error("Agent run stream is unavailable");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const rawEvent of events) {
      const parsed = parseSSE(rawEvent);
      if (parsed) onEvent(parsed);
    }
  }
  const parsed = parseSSE(buffer);
  if (parsed) onEvent(parsed);
}

function parseSSE(rawEvent: string): AgentRunEvent | null {
  const eventLine = rawEvent.split("\n").find((line) => line.startsWith("event: "));
  const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return null;
  return {
    event: eventLine.slice("event: ".length),
    data: JSON.parse(dataLine.slice("data: ".length))
  } as AgentRunEvent;
}

export function getRGMRecommendations(storeId: string): Promise<RGMRecommendationsResponse> {
  return request(`/api/v1/stores/${storeId}/rgm-recommendations`);
}

export function createOrderDraft(alert: OOSAlert, sessionId: string): Promise<OrderDraftResponse> {
  return request("/api/v1/orders/drafts", {
    method: "POST",
    body: JSON.stringify({
      store_id: alert.store_id,
      session_id: sessionId,
      items: [
        {
          sku_id: alert.sku_id,
          sku_name: alert.sku_name,
          quantity: 12,
          reason: alert.recommended_action
        }
      ],
      notes: `Drafted from alert ${alert.alert_id}`
    })
  });
}

export function approveOrderDraft(draftId: string): Promise<ApprovalResponse> {
  return request(`/api/v1/approvals/${draftId}/approve`, {
    method: "POST",
    body: JSON.stringify({ notes: "Approved from Phase 2 pilot workbench" })
  });
}

export function submitOrderDraftSandbox(draftId: string): Promise<SandboxSubmitResponse> {
  return request(`/api/v1/orders/drafts/${draftId}/submit-sandbox`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function syncFeedbackEvents(events: OfflineFeedbackEvent[]): Promise<unknown> {
  return request("/api/v1/sync/feedback-events", {
    method: "POST",
    body: JSON.stringify({ events })
  });
}

export function getPilotMetrics(): Promise<PilotMetricsResponse> {
  return request("/api/v1/metrics/pilot");
}

export function getTerritorySummary(): Promise<TerritorySummaryResponse> {
  return request(`/api/v1/manager/territory-summary?territory_code=${encodeURIComponent(getCurrentTerritory())}`);
}

export function getApprovalQueue(): Promise<ApprovalQueueResponse> {
  return request(`/api/v1/manager/approval-queue?territory_code=${encodeURIComponent(getCurrentTerritory())}`);
}

export function getManagerTasks(): Promise<ManagerTaskListResponse> {
  return request(`/api/v1/manager/tasks?territory_code=${encodeURIComponent(getCurrentTerritory())}`);
}

export function getMyManagerTasks(): Promise<ManagerTaskListResponse> {
  return request("/api/v1/manager/my-tasks");
}

export function createManagerTask(params: {
  store_id: string;
  assigned_rep_id: string;
  title: string;
  task_type: ManagerTask["task_type"];
  priority: ManagerTask["priority"];
  session_id: string;
  notes?: string | null;
  linked_alert_ids?: string[];
}): Promise<ManagerTask> {
  return request("/api/v1/manager/tasks", {
    method: "POST",
    body: JSON.stringify({
      territory_code: getCurrentTerritory(),
      store_id: params.store_id,
      assigned_rep_id: params.assigned_rep_id,
      session_id: params.session_id,
      title: params.title,
      task_type: params.task_type,
      priority: params.priority,
      notes: params.notes ?? null,
      linked_alert_ids: params.linked_alert_ids ?? []
    })
  });
}

export function updateManagerTaskStatus(
  taskId: string,
  status: "COMPLETED" | "BLOCKED" | "CANCELLED",
  sessionId: string,
  notes?: string
): Promise<ManagerTask> {
  return request(`/api/v1/manager/tasks/${encodeURIComponent(taskId)}/status`, {
    method: "POST",
    body: JSON.stringify({ status, session_id: sessionId, notes: notes ?? null })
  });
}

export function getAdminAuditEvents(filters?: {
  event_type?: string;
  rep_id?: string;
  resource_type?: string;
  cursor?: string | null;
  limit?: number;
}): Promise<AdminAuditEventsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(filters?.limit ?? 75));
  if (filters?.event_type) params.set("event_type", filters.event_type);
  if (filters?.rep_id) params.set("rep_id", filters.rep_id);
  if (filters?.resource_type) params.set("resource_type", filters.resource_type);
  if (filters?.cursor) params.set("cursor", filters.cursor);
  return request(`/api/v1/admin/audit-events?${params.toString()}`);
}

export function getAdminAuditEvent(eventId: string): Promise<AdminAuditEventDetailResponse> {
  return request(`/api/v1/admin/audit-events/${encodeURIComponent(eventId)}`);
}
