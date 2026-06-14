import type {
  AlertFeedback,
  AdminAuditEventsResponse,
  ApprovalResponse,
  DemoIdentity,
  DemoRole,
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

export function getAdminAuditEvents(): Promise<AdminAuditEventsResponse> {
  return request("/api/v1/admin/audit-events?limit=75");
}
