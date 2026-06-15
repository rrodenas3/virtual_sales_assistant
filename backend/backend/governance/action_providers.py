from __future__ import annotations

from backend.config import Settings, settings


def _crm_status(config: Settings) -> dict:
    blockers: list[str] = []
    if config.crm_adapter == "external":
        if not config.crm_endpoint:
            blockers.append("crm_endpoint")
        if not config.crm_token_ref:
            blockers.append("crm_token_ref")
        if not config.discovery_crm_platform:
            blockers.append("discovery_crm_platform")

    return {
        "provider": config.crm_adapter,
        "enabled": config.crm_adapter == "external",
        "endpoint_configured": bool(config.crm_endpoint),
        "token_ref_configured": bool(config.crm_token_ref),
        "discovery_configured": bool(config.discovery_crm_platform),
        "ready": not blockers,
        "blockers": blockers,
    }


def _erp_status(config: Settings) -> dict:
    blockers: list[str] = []
    if config.erp_adapter == "external":
        if not config.erp_endpoint:
            blockers.append("erp_endpoint")
        if not config.erp_token_ref:
            blockers.append("erp_token_ref")
        if not config.discovery_erp_sandbox:
            blockers.append("discovery_erp_sandbox")

    return {
        "provider": config.erp_adapter,
        "enabled": config.erp_adapter == "external",
        "endpoint_configured": bool(config.erp_endpoint),
        "token_ref_configured": bool(config.erp_token_ref),
        "discovery_configured": bool(config.discovery_erp_sandbox),
        "ready": not blockers,
        "blockers": blockers,
    }


def action_provider_status(config: Settings = settings) -> dict:
    crm = _crm_status(config)
    erp = _erp_status(config)
    return {
        "ready": crm["ready"] and erp["ready"],
        "crm": crm,
        "erp": erp,
        "blockers": [f"crm.{blocker}" for blocker in crm["blockers"]]
        + [f"erp.{blocker}" for blocker in erp["blockers"]],
    }
