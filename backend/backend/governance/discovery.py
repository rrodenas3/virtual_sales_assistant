from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.config import Settings, settings

GateStatus = Literal["answered", "defaulted", "missing"]


@dataclass(frozen=True)
class DiscoveryGate:
    topic: str
    setting_name: str
    status: GateStatus
    value: str | None
    required_for: tuple[str, ...]
    notes: str


def _gate(
    topic: str,
    setting_name: str,
    value: str | None,
    required_for: tuple[str, ...],
    notes: str,
    *,
    defaulted_values: tuple[str, ...] = (),
) -> DiscoveryGate:
    if value:
        status: GateStatus = "defaulted" if value in defaulted_values else "answered"
    else:
        status = "missing"
    return DiscoveryGate(topic, setting_name, status, value, required_for, notes)


def discovery_gates(config: Settings = settings) -> list[DiscoveryGate]:
    return [
        _gate(
            "Data sharing model",
            "discovery_data_sharing_model",
            config.discovery_data_sharing_model,
            ("databricks", "snowflake", "unity_catalog"),
            "Required before live data or audit integrations.",
        ),
        _gate(
            "CRM platform + OAuth",
            "discovery_crm_platform",
            config.discovery_crm_platform,
            ("crm_writeback",),
            "Required before CRM draft submit/write-back.",
        ),
        _gate(
            "ERP sandbox endpoint",
            "discovery_erp_sandbox",
            config.discovery_erp_sandbox,
            ("erp_submit",),
            "Required before real order submission.",
        ),
        _gate(
            "Pilot territory",
            "discovery_pilot_territory",
            config.discovery_pilot_territory,
            ("all_live_modes",),
            "Required to scope live reads and pilot rollout.",
            defaulted_values=("WEST-01",),
        ),
        _gate(
            "Rep device",
            "discovery_rep_device",
            config.discovery_rep_device,
            ("offline",),
            "Required before native/offline runtime decisions.",
            defaulted_values=("PWA",),
        ),
        _gate(
            "SSO provider",
            "discovery_sso_provider",
            config.discovery_sso_provider,
            ("external_jwt",),
            "Required before external JWT validation.",
        ),
        _gate(
            "Data residency",
            "discovery_data_residency",
            config.discovery_data_residency,
            ("databricks", "snowflake", "unity_catalog"),
            "Required before production data movement.",
        ),
        _gate(
            "Offline sync policy",
            "discovery_offline_sync_policy",
            config.discovery_offline_sync_policy,
            ("offline",),
            "Required before broader offline write queues.",
            defaulted_values=("browser-feedback-queue",),
        ),
    ]


def selected_live_modes(config: Settings = settings) -> set[str]:
    modes: set[str] = set()
    if config.auth_provider == "external_jwt":
        modes.add("external_jwt")
    if config.osa_adapter == "databricks" or config.rgm_adapter == "databricks":
        modes.add("databricks")
    if config.store_master_adapter == "snowflake":
        modes.add("snowflake")
    if config.audit_sink == "unity_catalog" or config.audit_dual_write_enabled:
        modes.add("unity_catalog")
    return modes


def readiness_blockers(config: Settings = settings) -> list[str]:
    modes = selected_live_modes(config)
    blockers: list[str] = []
    if not modes:
        return blockers
    for gate in discovery_gates(config):
        required = set(gate.required_for)
        applies = "all_live_modes" in required or bool(required & modes)
        if applies and gate.status == "missing":
            blockers.append(gate.setting_name)
    return blockers


def assert_discovery_ready(mode: str, config: Settings = settings) -> None:
    blockers = readiness_blockers(config)
    if blockers:
        raise RuntimeError(f"{mode} blocked by missing discovery gates: {', '.join(blockers)}")
