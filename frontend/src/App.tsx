import { AdminAuditView } from "./components/AdminAuditView";
import { AppHeader } from "./components/AppHeader";
import { ManagerCommandView } from "./components/ManagerCommandView";
import { RepWorkbenchView } from "./components/RepWorkbenchView";
import { TraceDrawer } from "./components/TraceDrawer";
import { useWorkbenchController } from "./hooks/useWorkbenchController";

export function App() {
  const workbench = useWorkbenchController();

  return (
    <main className="shell">
      <AppHeader
        identity={workbench.identity}
        role={workbench.role}
        online={workbench.online}
        queuedCount={workbench.queuedCount}
        pilotMetricLabel={workbench.pilotMetricLabel}
        onSwitchRole={workbench.switchRole}
        onOpenTrace={() => workbench.setTraceOpen(true)}
      />

      {workbench.error && <div className="errorBanner">{workbench.error}</div>}
      {workbench.cacheNotice && <div className="cacheBanner">{workbench.cacheNotice}</div>}
      {workbench.taskNotice && <div className="cacheBanner">{workbench.taskNotice}</div>}

      {workbench.role === "manager" && workbench.territorySummary && (
        <ManagerCommandView
          territorySummary={workbench.territorySummary}
          readiness={workbench.readiness}
          pilotGapReport={workbench.pilotGapReport}
          activationRunbook={workbench.activationRunbook}
          discoveryPacket={workbench.discoveryPacket}
          aiDemoActivationPack={workbench.aiDemoActivationPack}
          managerTasks={workbench.managerTasks}
          approvalQueue={workbench.approvalQueue}
          onOpenStore={workbench.openManagerStore}
          onAssignShelfCheck={workbench.assignShelfCheck}
          onCancelTask={(task) => workbench.changeTaskStatus(task, "CANCELLED")}
          onApproveDraft={workbench.approveQueueDraft}
        />
      )}

      {workbench.role === "admin" && workbench.adminAudit && (
        <AdminAuditView
          readiness={workbench.readiness}
          pilotGapReport={workbench.pilotGapReport}
          activationRunbook={workbench.activationRunbook}
          discoveryPacket={workbench.discoveryPacket}
          aiDemoActivationPack={workbench.aiDemoActivationPack}
          adminAudit={workbench.adminAudit}
          auditDetail={workbench.auditDetail}
          auditFilters={workbench.auditFilters}
          onFiltersChange={workbench.setAuditFilters}
          onOpenAuditDetail={workbench.openAuditDetail}
        />
      )}

      {workbench.role === "rep" && (
        <RepWorkbenchView
          agentRunEnabled={workbench.agentRunEnabled}
          visits={workbench.visits}
          selectedStoreId={workbench.selectedStoreId}
          selectedVisit={workbench.selectedVisit}
          store={workbench.store}
          alerts={workbench.alerts}
          rgm={workbench.rgm}
          summary={workbench.summary}
          agentEvents={workbench.agentEvents}
          agentRunning={workbench.agentRunning}
          agentError={workbench.agentError}
          draft={workbench.draft}
          approval={workbench.approval}
          submission={workbench.submission}
          feedback={workbench.feedback}
          myTasks={workbench.myTasks}
          onSelectStore={workbench.setSelectedStoreId}
          onTaskStatusChange={workbench.changeTaskStatus}
          onDraftTopAlert={workbench.draftTopAlert}
          onApproveDraft={workbench.approveDraft}
          onSubmitSandbox={workbench.submitSandbox}
          onRunAssistant={workbench.runAssistant}
          onRunAgentOrderDraft={workbench.runAgentOrderDraftForTopAlert}
          onRunAgentVisitLogDraft={workbench.runAgentVisitLogDraftForStore}
          onSummarize={workbench.summarize}
          onFeedback={workbench.handleFeedback}
        />
      )}

      <TraceDrawer
        open={workbench.traceOpen}
        onClose={() => workbench.setTraceOpen(false)}
        selectedVisit={workbench.selectedVisit}
        store={workbench.store}
        alerts={workbench.alerts}
        summaryAuditId={workbench.summary?.audit_event_id ?? null}
      />
    </main>
  );
}
