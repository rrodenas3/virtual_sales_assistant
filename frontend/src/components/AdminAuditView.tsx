import { ReadinessPanel } from "./ReadinessPanel";
import type {
  AdminAuditEventDetailResponse,
  AdminAuditEventsResponse,
  IntegrationReadinessResponse,
  PilotGapReport
} from "../lib/types";

type AuditFilters = {
  event_type: string;
  rep_id: string;
  resource_type: string;
};

export function AdminAuditView({
  readiness,
  pilotGapReport,
  adminAudit,
  auditDetail,
  auditFilters,
  onFiltersChange,
  onOpenAuditDetail
}: {
  readiness: IntegrationReadinessResponse | null;
  pilotGapReport: PilotGapReport | null;
  adminAudit: AdminAuditEventsResponse;
  auditDetail: AdminAuditEventDetailResponse | null;
  auditFilters: AuditFilters;
  onFiltersChange: (filters: AuditFilters) => void;
  onOpenAuditDetail: (eventId: string) => void;
}) {
  return (
    <section className="leadershipPane">
      {readiness && <ReadinessPanel readiness={readiness} pilotGapReport={pilotGapReport} variant="admin" />}
      <div className="sectionHead">
        <div>
          <p className="eyebrow">Audit</p>
          <h3>{adminAudit.events.length} recent events</h3>
        </div>
      </div>
      <div className="filterBar">
        <input
          placeholder="event type"
          value={auditFilters.event_type}
          onChange={(event) => onFiltersChange({ ...auditFilters, event_type: event.target.value })}
        />
        <input
          placeholder="rep id"
          value={auditFilters.rep_id}
          onChange={(event) => onFiltersChange({ ...auditFilters, rep_id: event.target.value })}
        />
        <input
          placeholder="resource type"
          value={auditFilters.resource_type}
          onChange={(event) => onFiltersChange({ ...auditFilters, resource_type: event.target.value })}
        />
      </div>
      <div className="auditFeed">
        {adminAudit.events.map((event) => (
          <button key={event.event_id} className="auditRow" onClick={() => onOpenAuditDetail(event.event_id)}>
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
  );
}
