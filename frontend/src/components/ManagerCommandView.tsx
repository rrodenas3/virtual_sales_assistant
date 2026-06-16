import { ReadinessPanel } from "./ReadinessPanel";
import type {
  ApprovalQueueResponse,
  IntegrationReadinessResponse,
  ManagerTask,
  ManagerTaskListResponse,
  PilotGapReport,
  TerritoryStoreSummary,
  TerritorySummaryResponse
} from "../lib/types";

export function ManagerCommandView({
  territorySummary,
  readiness,
  pilotGapReport,
  managerTasks,
  approvalQueue,
  onOpenStore,
  onAssignShelfCheck,
  onCancelTask,
  onApproveDraft
}: {
  territorySummary: TerritorySummaryResponse;
  readiness: IntegrationReadinessResponse | null;
  pilotGapReport: PilotGapReport | null;
  managerTasks: ManagerTaskListResponse | null;
  approvalQueue: ApprovalQueueResponse | null;
  onOpenStore: (row: TerritoryStoreSummary) => void;
  onAssignShelfCheck: (row: TerritoryStoreSummary) => void;
  onCancelTask: (task: ManagerTask) => void;
  onApproveDraft: (draftId: string) => void;
}) {
  return (
    <section className="leadershipPane">
      {readiness && <ReadinessPanel readiness={readiness} pilotGapReport={pilotGapReport} variant="manager" />}
      <div className="metricStrip">
        <div><span>Stores</span><strong>{territorySummary.store_count}</strong></div>
        <div><span>OOS alerts</span><strong>{territorySummary.total_oos_alerts}</strong></div>
        <div><span>Confirmed</span><strong>{territorySummary.confirmed_feedback_count}</strong></div>
        <div><span>Open drafts</span><strong>{territorySummary.open_draft_count}</strong></div>
      </div>
      <div className="managerTable">
        {territorySummary.stores.map((row) => (
          <button key={row.store_id} className="managerRow" onClick={() => onOpenStore(row)}>
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
              <button className="secondaryButton" data-testid={`assign-work-${row.store_id}`} onClick={() => onAssignShelfCheck(row)}>
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
                onClick={() => onCancelTask(task)}
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
                <button className="secondaryButton" onClick={() => onApproveDraft(item.draft_id)}>Approve</button>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
