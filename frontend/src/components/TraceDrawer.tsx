import { Activity, Database, GitBranch, X } from "lucide-react";
import type { OOSAlert, StoreDetail, VisitPriority } from "../lib/types";

type Props = {
  open: boolean;
  onClose: () => void;
  selectedVisit: VisitPriority | null;
  store: StoreDetail | null;
  alerts: OOSAlert[];
  summaryAuditId: string | null;
};

export function TraceDrawer({ open, onClose, selectedVisit, store, alerts, summaryAuditId }: Props) {
  if (!open) return null;

  return (
    <aside className="trace">
      <div className="trace__top">
        <div>
          <p className="eyebrow">Trace</p>
          <h2>Execution record</h2>
        </div>
        <button className="iconButton" onClick={onClose} aria-label="Close trace drawer">
          <X size={18} />
        </button>
      </div>

      <section className="traceBlock">
        <GitBranch size={18} />
        <div>
          <h3>Ranking formula</h3>
          <p>priority-v1: 40% OOS risk, 30% promo gap, 20% revenue opportunity, 10% visit recency.</p>
          {selectedVisit && (
            <dl className="componentGrid">
              <div><dt>OOS</dt><dd>{selectedVisit.components.oos_risk.toFixed(2)}</dd></div>
              <div><dt>Promo gap</dt><dd>{selectedVisit.components.promo_gap.toFixed(2)}</dd></div>
              <div><dt>Revenue</dt><dd>{selectedVisit.components.revenue_opportunity.toFixed(2)}</dd></div>
              <div><dt>Recency</dt><dd>{selectedVisit.components.visit_recency.toFixed(2)}</dd></div>
            </dl>
          )}
        </div>
      </section>

      <section className="traceBlock">
        <Database size={18} />
        <div>
          <h3>Data source</h3>
          <p>{alerts[0]?.source_system ?? "mock"} / {alerts[0]?.model_version ?? "mock-v1"}</p>
          <p>Freshness: {store ? new Date(store.data_freshness_ts).toLocaleString() : "No store selected"}</p>
        </div>
      </section>

      <section className="traceBlock">
        <Activity size={18} />
        <div>
          <h3>Audit links</h3>
          <p>Store audit: {store?.audit_event_id ?? "None"}</p>
          <p>Summary audit: {summaryAuditId ?? "None"}</p>
          <p>{alerts.length} alert rows loaded. First row: {alerts[0]?.prediction_row_id ?? "None"}</p>
        </div>
      </section>
    </aside>
  );
}

