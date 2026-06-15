from __future__ import annotations

from backend.config import Settings, settings


def shelf_image_status(config: Settings = settings) -> dict:
    blockers: list[str] = []
    if config.shelf_image_adapter == "external":
        if not config.shelf_image_endpoint:
            blockers.append("shelf_image_endpoint")
        if not config.shelf_image_token_ref:
            blockers.append("shelf_image_token_ref")
        if not config.discovery_rep_device:
            blockers.append("discovery_rep_device")
        if not config.discovery_data_residency:
            blockers.append("discovery_data_residency")

    return {
        "provider": config.shelf_image_adapter,
        "external_enabled": config.shelf_image_adapter == "external",
        "endpoint_configured": bool(config.shelf_image_endpoint),
        "token_ref_configured": bool(config.shelf_image_token_ref),
        "timeout_seconds": config.shelf_image_timeout_seconds,
        "device_configured": bool(config.discovery_rep_device),
        "data_residency_configured": bool(config.discovery_data_residency),
        "ready": not blockers,
        "blockers": blockers,
    }
