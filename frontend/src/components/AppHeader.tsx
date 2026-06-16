import { Database, ShieldCheck } from "lucide-react";

import type { DemoIdentity, DemoRole } from "../lib/types";

export function AppHeader({
  identity,
  role,
  online,
  queuedCount,
  pilotMetricLabel,
  onSwitchRole,
  onOpenTrace
}: {
  identity: DemoIdentity;
  role: DemoRole;
  online: boolean;
  queuedCount: number;
  pilotMetricLabel: string;
  onSwitchRole: (role: DemoRole) => void;
  onOpenTrace: () => void;
}) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">PHANTOM / {identity.territory_code ?? "all territories"} / {identity.sub}</p>
        <h1>{role === "rep" ? "Today's field workbench" : role === "manager" ? "Territory command view" : "Governance audit view"}</h1>
      </div>
      <div className="topbar__actions">
        <div className="roleSwitch">
          {(["rep", "manager", "admin"] as DemoRole[]).map((item) => (
            <button key={item} className={role === item ? "roleSwitch__item roleSwitch__item--active" : "roleSwitch__item"} onClick={() => onSwitchRole(item)}>
              {item}
            </button>
          ))}
        </div>
        <button className="secondaryButton" onClick={onOpenTrace}>
          <Database size={16} /> Trace
        </button>
        <div className="statusPill"><ShieldCheck size={16} /> Mock JWT active</div>
        <div className={online ? "statusPill" : "statusPill statusPill--offline"}>
          {online ? "Online" : "Offline"} / queued {queuedCount}
        </div>
        <div className="statusPill">{pilotMetricLabel}</div>
      </div>
    </header>
  );
}
