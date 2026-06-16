import type {
  AIDemoActivationPack,
  ActivationRunbook,
  DiscoveryPacket,
  IntegrationReadinessResponse,
  PilotGapReport
} from "../lib/types";

const TARGETS = ["local", "ai-demo", "pilot"] as const;

function previewList(values: string[], visibleCount: number): string[] {
  if (values.length <= visibleCount) return values;
  const headCount = Math.max(visibleCount - 1, 1);
  return [...values.slice(0, headCount), values[values.length - 1]];
}

function ActivationTargets({ readiness }: { readiness: IntegrationReadinessResponse }) {
  return (
    <div className="activationTargets" data-testid="activation-targets">
      {readiness.activation_targets.map((target) => (
        <div key={target.target} className={target.ready ? "activationTarget activationTarget--ready" : "activationTarget"}>
          <strong>{target.target}</strong>
          <span>{target.ready ? "ready" : `${target.blockers.length} blockers`}</span>
          {target.blockers.length > 0 && (
            <small>{target.blockers.slice(0, 2).join("; ")}</small>
          )}
        </div>
      ))}
    </div>
  );
}

function RuntimeCommands({ readiness }: { readiness: IntegrationReadinessResponse }) {
  return (
    <div className="runtimeCommands" data-testid="runtime-commands">
      {TARGETS.map((target) => {
        const commands = readiness.runtime_validation_commands[target];
        const nextCommand = commands[0];
        return (
          <div key={target} className="runtimeCommandGroup">
            <div className="runtimeCommandGroup__top">
              <strong>{target}</strong>
              <span>{commands.length} commands</span>
            </div>
            <div className="commandChips">
              {commands.slice(0, 5).map((command) => (
                <span key={command.name}>{command.name}</span>
              ))}
              {commands.length > 5 && <span>+{commands.length - 5}</span>}
            </div>
            {nextCommand && (
              <>
                <small>next {nextCommand.name}</small>
                <code aria-label={`${target} next validation command`}>{nextCommand.command}</code>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ActivationEvidence({ readiness }: { readiness: IntegrationReadinessResponse }) {
  return (
    <div className="activationEvidenceGrid" data-testid="activation-evidence">
      {TARGETS.map((target) => {
        const manifest = readiness.activation_evidence_manifests[target];
        const artifacts = previewList(manifest.required_artifacts, 3);
        const envKeys = previewList(manifest.required_env_keys, 4);
        return (
          <div key={target} className="activationEvidenceGroup">
            <div className="runtimeCommandGroup__top">
              <strong>{target} evidence</strong>
              <span>{manifest.sections.length} sections</span>
            </div>
            <div className="commandChips">
              {manifest.sections.map((section) => (
                <span key={section.name}>{section.name}</span>
              ))}
            </div>
            <small>
              {manifest.required_artifacts.length} artifacts / {manifest.required_env_keys.length} env keys
            </small>
            {artifacts.length > 0 && (
              <ul className="evidenceList" aria-label={`${target} required artifacts`}>
                {artifacts.map((artifact) => (
                  <li key={artifact}>{artifact}</li>
                ))}
              </ul>
            )}
            {envKeys.length > 0 && (
              <ul className="evidenceList evidenceList--env" aria-label={`${target} required env keys`}>
                {envKeys.map((envKey) => (
                  <li key={envKey}>{envKey}</li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

function discoveryOwnerSummary(readiness: IntegrationReadinessResponse): string | null {
  if (readiness.blockers.length === 0) return null;
  const blockerSet = new Set(readiness.blockers);
  const counts = readiness.gates
    .filter((gate) => blockerSet.has(gate.setting_name))
    .reduce<Record<string, number>>((acc, gate) => {
      acc[gate.owner] = (acc[gate.owner] ?? 0) + 1;
      return acc;
    }, {});
  const parts = Object.entries(counts).map(([owner, count]) => `${count} ${owner}`);
  return parts.length ? `Discovery owners: ${parts.join(", ")}` : null;
}

function AIDemoEvidence({ readiness }: { readiness: IntegrationReadinessResponse }) {
  return (
    <div className="readinessEvidence" data-testid="ai-demo-evidence">
      <span className={readiness.ai_demo_provider_ready ? "evidencePill evidencePill--ready" : "evidencePill"}>
        {readiness.ai_demo_provider_ready ? "AI provider configured" : "AI provider blocked"}
      </span>
      <span className={readiness.ai_demo_eval_validated ? "evidencePill evidencePill--ready" : "evidencePill"}>
        {readiness.ai_demo_eval_validated ? "AI eval validated" : "AI eval pending"}
      </span>
      <span className="evidencePill">stage {readiness.ai_demo_stage}</span>
      {readiness.ai_demo_next_actions[0] && <span className="evidencePill">{readiness.ai_demo_next_actions[0]}</span>}
      {readiness.ai_demo_eval_validation_summary && <span className="evidencePill">{readiness.ai_demo_eval_validation_summary}</span>}
    </div>
  );
}

function AIDemoActivationSummary({ pack }: { pack: AIDemoActivationPack }) {
  const visibleChecks = pack.config_checks.slice(0, 6);
  return (
    <div className="aiDemoPack" data-testid="ai-demo-activation-pack">
      <div className="runtimeCommandGroup__top">
        <strong>AI demo activation</strong>
        <span>{pack.ready ? "ready" : `${pack.blockers.length} blockers`}</span>
      </div>
      <small>{pack.stage} / {pack.summary_provider} / {pack.summary_model_id}</small>
      <div className="aiDemoPackGrid">
        <div>
          <div className="commandChips">
            {visibleChecks.map((check) => (
              <span key={check.name} className={check.ready ? "commandChip--ready" : ""}>
                {check.name}
              </span>
            ))}
          </div>
          {pack.next_actions[0] && <small>{pack.next_actions[0]}</small>}
        </div>
        <div>
          <ul className="evidenceList evidenceList--env" aria-label="ai demo required commands">
            {pack.required_commands.slice(0, 4).map((command) => (
              <li key={command.name}>{command.name}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function PilotGapSummary({ report }: { report: PilotGapReport }) {
  const owners = Array.from(new Set(report.blocking_gaps.map((gap) => gap.owner)));
  const topGaps = report.blocking_gaps.slice(0, 4);
  const topCommands = report.recommended_commands.slice(0, 4);
  return (
    <div className="pilotGapSummary" data-testid="pilot-gap-summary">
      <div className="runtimeCommandGroup__top">
        <strong>{report.target} gap report</strong>
        <span>{report.gap_count} gaps</span>
      </div>
      <div className="readinessEvidence">
        <span className={report.ready_for_requested_target ? "evidencePill evidencePill--ready" : "evidencePill"}>
          {report.ready_for_requested_target ? "target ready" : `${report.requested_target_blocker_count} target blockers`}
        </span>
        {owners.map((owner) => (
          <span key={owner} className="evidencePill">{owner}</span>
        ))}
      </div>
      <div className="pilotGapGrid">
        <ul className="evidenceList" aria-label="pilot gap blockers">
          {topGaps.map((gap) => (
            <li key={`${gap.target}-${gap.blocker}`}>{gap.target}: {gap.blocker}</li>
          ))}
        </ul>
        <ul className="evidenceList evidenceList--env" aria-label="pilot gap commands">
          {topCommands.map((command) => (
            <li key={command.name}>{command.name}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ActivationRunbookSummary({ runbook }: { runbook: ActivationRunbook }) {
  const visiblePhases = runbook.phases.slice(0, 6);
  return (
    <div className="activationRunbook" data-testid="activation-runbook">
      <div className="runtimeCommandGroup__top">
        <strong>Final VSA runbook</strong>
        <span>{runbook.ready_phase_count}/{runbook.phase_count} ready</span>
      </div>
      <small>{runbook.blocked_phase_count} blocked phases / target {runbook.current_target}</small>
      <div className="activationRunbookGrid">
        {visiblePhases.map((phase) => (
          <article key={phase.phase_id} className={`activationRunbookPhase activationRunbookPhase--${phase.status}`}>
            <div className="runtimeCommandGroup__top">
              <strong>{phase.title}</strong>
              <span>{phase.status}</span>
            </div>
            <small>{phase.owner} / {phase.estimated_effort}</small>
            <div className="commandChips">
              {phase.required_command_names.slice(0, 3).map((commandName) => (
                <span key={commandName}>{commandName}</span>
              ))}
              {phase.required_command_names.length > 3 && <span>+{phase.required_command_names.length - 3}</span>}
            </div>
            {phase.blockers[0] && <small>{phase.blockers[0]}</small>}
          </article>
        ))}
      </div>
    </div>
  );
}

function DiscoveryPacketSummary({ packet }: { packet: DiscoveryPacket }) {
  return (
    <div className="discoveryPacket" data-testid="discovery-packet">
      <div className="runtimeCommandGroup__top">
        <strong>{packet.target} discovery packet</strong>
        <span>{packet.missing_count} missing</span>
      </div>
      <small>{packet.gate_count} gates / {packet.defaulted_count} defaulted / {packet.selected_live_modes.join(", ") || "no live modes selected"}</small>
      <div className="discoveryPacketGrid">
        {packet.owner_groups.map((group) => (
          <article key={group.owner} className="discoveryOwnerGroup">
            <div className="runtimeCommandGroup__top">
              <strong>{group.owner}</strong>
              <span>{group.missing_count} missing</span>
            </div>
            <div className="commandChips">
              {group.gates.slice(0, 4).map((gate) => (
                <span key={gate.setting_name}>{gate.setting_name}</span>
              ))}
              {group.gates.length > 4 && <span>+{group.gates.length - 4}</span>}
            </div>
          </article>
        ))}
      </div>
      {packet.next_actions[0] && <small>{packet.next_actions[0]}</small>}
    </div>
  );
}

export function ReadinessPanel({
  readiness,
  pilotGapReport,
  activationRunbook,
  discoveryPacket,
  aiDemoActivationPack,
  variant
}: {
  readiness: IntegrationReadinessResponse;
  pilotGapReport: PilotGapReport | null;
  activationRunbook: ActivationRunbook | null;
  discoveryPacket: DiscoveryPacket | null;
  aiDemoActivationPack: AIDemoActivationPack | null;
  variant: "manager" | "admin";
}) {
  const readinessOwnerSummary = discoveryOwnerSummary(readiness);
  const readinessBlockers = [...readiness.blockers, ...readiness.provider_blockers, ...readiness.ai_demo_blockers];
  const isManager = variant === "manager";
  let heading = readiness.ready ? "Provider gates clear" : "Provider review required";
  if (isManager) {
    heading = readiness.ready ? "Local scaffold ready" : "Action required";
  }

  return (
    <div className="readinessPanel" data-testid={isManager ? "readiness-panel" : "admin-readiness-panel"}>
      <div>
        <p className="eyebrow">{isManager ? "Pilot readiness" : "Governance readiness"}</p>
        <h3>{heading}</h3>
      </div>
      <div className="readinessPanel__meta">
        {isManager ? (
          <>
            <span>{readiness.selected_live_modes.length ? readiness.selected_live_modes.join(", ") : "mock/local modes"}</span>
            <span>{readiness.provider_blockers.length} provider blockers</span>
            <span>{readiness.ai_demo_ready ? "AI demo ready" : `${readiness.summary_provider} summary`}</span>
          </>
        ) : (
          <>
            <span>{readiness.provider_blockers.length} provider blockers</span>
            <span>{readiness.blockers.length} discovery blockers</span>
            <span>{readiness.view_contract_validated ? "live contracts validated" : "mock contracts"}</span>
          </>
        )}
        {readinessOwnerSummary && <span>{readinessOwnerSummary}</span>}
      </div>
      <AIDemoEvidence readiness={readiness} />
      {readinessBlockers.length > 0 && (
        <div className="readinessPanel__blockers">
          {readinessBlockers.slice(0, 4).map((blocker) => (
            <span key={blocker}>{blocker}</span>
          ))}
        </div>
      )}
      {aiDemoActivationPack && <AIDemoActivationSummary pack={aiDemoActivationPack} />}
      {pilotGapReport && <PilotGapSummary report={pilotGapReport} />}
      {activationRunbook && <ActivationRunbookSummary runbook={activationRunbook} />}
      {discoveryPacket && <DiscoveryPacketSummary packet={discoveryPacket} />}
      <ActivationTargets readiness={readiness} />
      <RuntimeCommands readiness={readiness} />
      <ActivationEvidence readiness={readiness} />
    </div>
  );
}
