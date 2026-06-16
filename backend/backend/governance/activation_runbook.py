from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from backend.config import settings

ActivationTargetName = Literal["local", "ai-demo", "pilot"]
PhaseStatus = Literal["ready", "blocked", "scaffolded", "deferred"]
Owner = Literal["engineering", "delivery", "delivery+engineering"]


class ActivationRunbookPhase(TypedDict):
    phase_id: str
    title: str
    target: ActivationTargetName
    owner: Owner
    estimated_effort: str
    goal: str
    status: PhaseStatus
    required_command_names: list[str]
    required_configuration_keys: list[str]
    exit_gate_summary: list[str]
    blockers: list[str]


class ActivationRunbook(TypedDict):
    generated_at: str
    current_target: ActivationTargetName
    final_outcome: str
    phase_count: int
    ready_phase_count: int
    blocked_phase_count: int
    phases: list[ActivationRunbookPhase]
    public_safety_notes: list[str]


def build_activation_runbook(
    *,
    current_target: ActivationTargetName,
    activation_targets: list[dict[str, Any]],
    provider_readiness: dict[str, dict[str, Any]],
    runtime_validation_commands: dict[ActivationTargetName, list[dict[str, str]]],
) -> ActivationRunbook:
    target_blockers = {
        str(target["target"]): list(target.get("blockers", []))
        for target in activation_targets
    }
    command_names = {
        target: [command["name"] for command in commands]
        for target, commands in runtime_validation_commands.items()
    }
    phases = [
        _phase(
            phase_id="phase-0-local-scaffold",
            title="Local Scaffold Readiness",
            target="local",
            owner="engineering",
            estimated_effort="same day after each implementation chunk",
            goal="Prove the mock-backed workbench, audit, HITL, offline shell, and grounded summary path still work.",
            status="ready" if not target_blockers.get("local", []) else "blocked",
            required_command_names=[
                "local_readiness",
                "api_contract",
                "final_api_smoke",
                "local_dev_smoke",
                "readiness_bundle",
                "validation_suite",
            ],
            available_command_names=command_names["local"],
            required_configuration_keys=[],
            exit_gate_summary=[
                "Local readiness report passes.",
                "API contract validation proves the running backend is current.",
                "Final API smoke covers rep, manager, admin, HITL, audit, feedback, CRM draft, RGM, and metrics paths.",
            ],
            blockers=target_blockers.get("local", []),
        ),
        _phase(
            phase_id="phase-1-ai-demo",
            title="Real AI Demo Readiness",
            target="ai-demo",
            owner="delivery+engineering",
            estimated_effort="1-2 engineering days after approved model access is available",
            goal="Prove the assistant is more than a deterministic template while retaining grounding, traceability, latency, and cost controls.",
            status="ready" if not target_blockers.get("ai-demo", []) else "blocked",
            required_command_names=[
                "ai_summary_eval",
                "mlflow_handoff_dry_run",
                "ai_demo_eval_evidence",
                "summary_load_test",
                "ai_demo_readiness",
            ],
            available_command_names=command_names["ai-demo"],
            required_configuration_keys=[
                "SUMMARY_PROVIDER",
                "ANTHROPIC_TOKEN_REF",
                "ANTHROPIC_MODEL",
                "SUMMARY_FAIL_OPEN",
                "AI_DEMO_EVAL_VALIDATED",
            ],
            exit_gate_summary=[
                "Approved-provider eval passes with provider=anthropic.",
                "Hallucination rate remains 0.0 and trace completeness remains 1.0.",
                "P95 summary latency remains below 5000 ms and cost stays under the configured ceiling.",
            ],
            blockers=target_blockers.get("ai-demo", []),
        ),
        _provider_phase(
            phase_id="phase-2-live-data-contracts",
            title="Live Data Contract Readiness",
            owner="delivery+engineering",
            estimated_effort="2-5 engineering days after platform access and view names are confirmed",
            goal="Prove selected Databricks and Snowflake views match the corrected ontology before pilot users see live data.",
            provider=provider_readiness.get("data_platform", {}),
            ready=bool(settings.live_data_contract_validated and provider_readiness.get("data_platform", {}).get("ready", False)),
            default_status="blocked",
            required_command_names=["live_data_contracts"],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[
                "OSA_ADAPTER",
                "RGM_ADAPTER",
                "STORE_MASTER_ADAPTER",
                "DISCOVERY_DATA_SHARING_MODEL",
                "DISCOVERY_DATA_RESIDENCY",
                "LIVE_DATA_CONTRACT_VALIDATED",
            ],
            exit_gate_summary=[
                "Required columns, normalized scores, rep filters, territory filters, and alert business keys validate.",
                "Credentialed validation writes public-safe readiness artifacts.",
                "No SQL string interpolation is introduced in live adapters.",
            ],
        ),
        _provider_phase(
            phase_id="phase-3-identity-governance",
            title="Identity And Governance Readiness",
            owner="delivery+engineering",
            estimated_effort="2-4 engineering days after SSO and audit target details are approved",
            goal="Move from mock identity and local audit to client-governed identity and auditable mirror.",
            provider=_combined_provider_status(provider_readiness, ["auth", "audit", "guardrails"]),
            ready=_providers_ready(provider_readiness, ["auth", "audit", "guardrails"])
            and bool(provider_readiness.get("audit", {}).get("unity_selected", False)),
            default_status="blocked",
            required_command_names=["unity_audit_smoke", "guardrail_classifier_smoke"],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[
                "AUTH_PROVIDER",
                "EXTERNAL_JWT_ISSUER",
                "EXTERNAL_JWT_AUDIENCE",
                "EXTERNAL_JWT_JWKS_URL",
                "AUDIT_DUAL_WRITE_ENABLED",
                "AUDIT_UNITY_CATALOG_TABLE",
                "GUARDRAIL_CLASSIFIER_BLOCK_THRESHOLD",
            ],
            exit_gate_summary=[
                "Unauthorized store access still returns 404.",
                "Unity Catalog audit mirror is selected and smoke-tested before credentialed write.",
                "Guardrail classifier is explicitly deferred or ready with the 0.85 block threshold.",
            ],
        ),
        _provider_phase(
            phase_id="phase-4-crm-erp-hitl",
            title="CRM, ERP, And HITL Write-Back",
            owner="delivery+engineering",
            estimated_effort="3-7 engineering days after sandbox endpoints and OAuth flow are confirmed",
            goal="Preserve the existing HITL invariant while enabling real draft/write-back integrations.",
            provider=provider_readiness.get("action_providers", {}),
            ready=bool(provider_readiness.get("action_providers", {}).get("ready", False)),
            default_status="scaffolded",
            required_command_names=["action_provider_smoke"],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[
                "CRM_ADAPTER",
                "ERP_ADAPTER",
                "DISCOVERY_CRM_PLATFORM",
                "DISCOVERY_ERP_SANDBOX",
            ],
            exit_gate_summary=[
                "Agents can draft but cannot submit.",
                "Approval payload hash must match at submit time.",
                "External write failures are audited and do not mutate approval history.",
            ],
        ),
        _provider_phase(
            phase_id="phase-5-offline-memory",
            title="Offline And Memory Expansion",
            owner="delivery+engineering",
            estimated_effort="3-6 engineering days after device and retention decisions are confirmed",
            goal="Make the pilot robust during store visits without uncontrolled local inference or persistent-memory risk.",
            provider=_combined_provider_status(provider_readiness, ["memory", "offline_agent"]),
            ready=_providers_ready(provider_readiness, ["memory", "offline_agent"]),
            default_status="scaffolded",
            required_command_names=["memory_provider_smoke"],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[
                "MEMORY_PROVIDER",
                "DISCOVERY_MEMORY_RETENTION_POLICY",
                "DISCOVERY_MEMORY_SCOPES",
                "MEM0_TOKEN_REF",
                "OFFLINE_AGENT_PROVIDER",
                "OFFLINE_AGENT_KILL_SWITCH",
            ],
            exit_gate_summary=[
                "IndexedDB read cache works for route, store, alerts, and RGM data.",
                "Feedback sync remains idempotent with rep identity and client event UUID.",
                "Memory activation is scoped and visible through health/readiness gates.",
            ],
        ),
        _provider_phase(
            phase_id="phase-5b-shelf-image",
            title="Shelf Image Provider Readiness",
            owner="delivery+engineering",
            estimated_effort="2-4 engineering days after device, image-retention, and data-residency decisions are confirmed",
            goal="Add image-assisted shelf review without allowing image-only replenishment decisions.",
            provider=provider_readiness.get("shelf_image", {}),
            ready=bool(provider_readiness.get("shelf_image", {}).get("ready", False)),
            default_status="scaffolded",
            required_command_names=[],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[
                "SHELF_IMAGE_ADAPTER",
                "SHELF_IMAGE_ENDPOINT",
                "SHELF_IMAGE_TOKEN_REF",
                "DISCOVERY_REP_DEVICE",
                "DISCOVERY_DATA_RESIDENCY",
            ],
            exit_gate_summary=[
                "External provider receives only approved image references plus grounded OOS context.",
                "Findings either reference supplied alert IDs or are labeled unknown/low.",
                "Image findings cannot create orders without the existing HITL flow.",
            ],
        ),
        _phase(
            phase_id="phase-6-final-pilot",
            title="Final VSA Pilot Gate",
            target="pilot",
            owner="delivery+engineering",
            estimated_effort="1-2 days after phases 1-5 are green",
            goal="Joint engineering and delivery signoff before pilot traffic.",
            status="ready" if not target_blockers.get("pilot", []) else "blocked",
            required_command_names=[
                "pilot_readiness",
                "final_api_smoke",
                "unity_audit_smoke",
                "action_provider_smoke",
                "guardrail_classifier_smoke",
                "memory_provider_smoke",
                "pilot_env_handoff",
            ],
            available_command_names=command_names["pilot"],
            required_configuration_keys=[],
            exit_gate_summary=[
                "Rep, manager, and admin workflows work with approved identity and governed integrations.",
                "Every AI summary and write intent is grounded, audited, cost-tracked, and tied to identity.",
                "Pilot validation env snippet contains only non-secret validation evidence.",
            ],
            blockers=target_blockers.get("pilot", []),
        ),
    ]
    ready_count = sum(1 for phase in phases if phase["status"] == "ready")
    blocked_count = sum(1 for phase in phases if phase["status"] == "blocked")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "current_target": current_target,
        "final_outcome": (
            "A governed VSA pilot where reps prioritize stores, inspect grounded OOS/RGM recommendations, "
            "run the SSE assistant, submit feedback, create HITL-gated drafts, and work through brief offline periods."
        ),
        "phase_count": len(phases),
        "ready_phase_count": ready_count,
        "blocked_phase_count": blocked_count,
        "phases": phases,
        "public_safety_notes": [
            "Runbook output includes only setting names, command names, owner labels, and public-safe blocker text.",
            "Secrets, bearer tokens, endpoint credentials, local user paths, and confidential client identifiers are not included.",
        ],
    }


def _phase(
    *,
    phase_id: str,
    title: str,
    target: ActivationTargetName,
    owner: Owner,
    estimated_effort: str,
    goal: str,
    status: PhaseStatus,
    required_command_names: list[str],
    available_command_names: list[str],
    required_configuration_keys: list[str],
    exit_gate_summary: list[str],
    blockers: list[str],
) -> ActivationRunbookPhase:
    known_required_commands = [name for name in required_command_names if name in available_command_names]
    return {
        "phase_id": phase_id,
        "title": title,
        "target": target,
        "owner": owner,
        "estimated_effort": estimated_effort,
        "goal": goal,
        "status": status,
        "required_command_names": known_required_commands,
        "required_configuration_keys": required_configuration_keys,
        "exit_gate_summary": exit_gate_summary,
        "blockers": blockers,
    }


def _provider_phase(
    *,
    phase_id: str,
    title: str,
    owner: Owner,
    estimated_effort: str,
    goal: str,
    provider: dict[str, Any],
    ready: bool,
    default_status: PhaseStatus,
    required_command_names: list[str],
    available_command_names: list[str],
    required_configuration_keys: list[str],
    exit_gate_summary: list[str],
) -> ActivationRunbookPhase:
    blockers = [str(blocker) for blocker in provider.get("blockers", [])]
    status: PhaseStatus = "ready" if ready else default_status
    if blockers or (default_status == "blocked" and not ready):
        status = "blocked"
    if status == "blocked" and not blockers:
        blockers = ["Required configuration or validation evidence is not yet recorded"]
    return _phase(
        phase_id=phase_id,
        title=title,
        target="pilot",
        owner=owner,
        estimated_effort=estimated_effort,
        goal=goal,
        status=status,
        required_command_names=required_command_names,
        available_command_names=available_command_names,
        required_configuration_keys=required_configuration_keys,
        exit_gate_summary=exit_gate_summary,
        blockers=blockers,
    )


def _combined_provider_status(provider_readiness: dict[str, dict[str, Any]], names: list[str]) -> dict[str, Any]:
    blockers: list[str] = []
    for name in names:
        for blocker in provider_readiness.get(name, {}).get("blockers", []):
            blockers.append(f"{name}.{blocker}")
    return {"blockers": blockers}


def _providers_ready(provider_readiness: dict[str, dict[str, Any]], names: list[str]) -> bool:
    return all(bool(provider_readiness.get(name, {}).get("ready", False)) for name in names)
