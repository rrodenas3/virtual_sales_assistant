from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypedDict

from backend.governance.discovery import DiscoveryGate, GateOwner, discovery_gates, selected_live_modes

Target = Literal["local", "ai-demo", "pilot"]

PILOT_REQUIRED_MODES = {
    "all_live_modes",
    "databricks",
    "snowflake",
    "unity_catalog",
    "crm_writeback",
    "erp_submit",
    "external_jwt",
    "offline",
    "offline_agent",
    "mem0",
    "shelf_image",
    "guardrail_classifier",
}


class DiscoveryPacketGate(TypedDict):
    topic: str
    setting_name: str
    status: str
    value_present: bool
    required_for: list[str]
    notes: str
    owner: GateOwner


class DiscoveryOwnerGroup(TypedDict):
    owner: GateOwner
    gate_count: int
    missing_count: int
    defaulted_count: int
    gates: list[DiscoveryPacketGate]


class DiscoveryPacket(TypedDict):
    generated_at: str
    target: Target
    selected_live_modes: list[str]
    gate_count: int
    missing_count: int
    defaulted_count: int
    owner_groups: list[DiscoveryOwnerGroup]
    next_actions: list[str]
    public_safety_notes: list[str]


def build_discovery_packet(target: Target) -> DiscoveryPacket:
    gates = _target_gates(target)
    packet_gates = [_packet_gate(gate) for gate in gates]
    owner_groups = [_owner_group(owner, packet_gates) for owner in ("delivery", "engineering", "shared")]
    owner_groups = [group for group in owner_groups if group["gate_count"] > 0]
    missing_count = sum(1 for gate in packet_gates if gate["status"] == "missing")
    defaulted_count = sum(1 for gate in packet_gates if gate["status"] == "defaulted")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "selected_live_modes": sorted(selected_live_modes()),
        "gate_count": len(packet_gates),
        "missing_count": missing_count,
        "defaulted_count": defaulted_count,
        "owner_groups": owner_groups,
        "next_actions": _next_actions(target, owner_groups),
        "public_safety_notes": [
            "Discovery packet includes setting names, status, owner, and non-secret value presence only.",
            "Actual values, endpoint URLs, tokens, local paths, and client-confidential identifiers are not included.",
        ],
    }


def _target_gates(target: Target) -> list[DiscoveryGate]:
    gates = discovery_gates()
    if target == "local":
        return [gate for gate in gates if gate.status == "defaulted"]
    if target == "ai-demo":
        return [
            gate
            for gate in gates
            if "all_live_modes" in gate.required_for or "external_jwt" in gate.required_for
        ]
    return [
        gate
        for gate in gates
        if "all_live_modes" in gate.required_for or bool(set(gate.required_for) & PILOT_REQUIRED_MODES)
    ]


def _packet_gate(gate: DiscoveryGate) -> DiscoveryPacketGate:
    return {
        "topic": gate.topic,
        "setting_name": gate.setting_name,
        "status": gate.status,
        "value_present": bool(gate.value),
        "required_for": list(gate.required_for),
        "notes": gate.notes,
        "owner": gate.owner,
    }


def _owner_group(owner: GateOwner, gates: list[DiscoveryPacketGate]) -> DiscoveryOwnerGroup:
    owned_gates = [gate for gate in gates if gate["owner"] == owner]
    return {
        "owner": owner,
        "gate_count": len(owned_gates),
        "missing_count": sum(1 for gate in owned_gates if gate["status"] == "missing"),
        "defaulted_count": sum(1 for gate in owned_gates if gate["status"] == "defaulted"),
        "gates": owned_gates,
    }


def _next_actions(target: Target, owner_groups: list[DiscoveryOwnerGroup]) -> list[str]:
    actions: list[str] = []
    for group in owner_groups:
        missing = [gate["setting_name"] for gate in group["gates"] if gate["status"] == "missing"]
        if missing:
            actions.append(f"{group['owner']}: answer {', '.join(missing[:4])}")
    if not actions:
        actions.append(f"No missing discovery gates for {target}")
    return actions
