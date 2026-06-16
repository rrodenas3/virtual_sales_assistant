import type { IntegrationReadinessResponse } from "../lib/types";

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
  const targets = ["local", "ai-demo", "pilot"] as const;
  return (
    <div className="runtimeCommands" data-testid="runtime-commands">
      {targets.map((target) => {
        const commands = readiness.runtime_validation_commands[target];
        const nextCommand = commands[0];
        return (
          <div key={target} className="runtimeCommandGroup">
            <strong>{target}</strong>
            <span>{commands.map((command) => command.name).join(", ")}</span>
            {nextCommand && (
              <code aria-label={`${target} next validation command`}>{nextCommand.command}</code>
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

export function ReadinessPanel({
  readiness,
  variant
}: {
  readiness: IntegrationReadinessResponse;
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
      <ActivationTargets readiness={readiness} />
      <RuntimeCommands readiness={readiness} />
    </div>
  );
}
