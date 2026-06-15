from __future__ import annotations

from backend.config import Settings, settings


def offline_agent_status(config: Settings = settings) -> dict:
    blockers: list[str] = []
    if not config.offline_agent_enabled:
        blockers.append("OFFLINE_AGENT_ENABLED must be true after spike approval")
    if config.offline_agent_provider == "none":
        blockers.append("OFFLINE_AGENT_PROVIDER must be hermes or ollama after spike approval")
    if config.offline_agent_kill_switch:
        blockers.append("OFFLINE_AGENT_KILL_SWITCH must be false only after explicit approval")
    if config.offline_agent_min_device_ram_gb < 8:
        blockers.append("OFFLINE_AGENT_MIN_DEVICE_RAM_GB must be at least 8")
    if config.offline_agent_max_latency_ms > 2500:
        blockers.append("OFFLINE_AGENT_MAX_LATENCY_MS must be 2500 or lower")
    if config.offline_agent_min_tool_accuracy < 0.95:
        blockers.append("OFFLINE_AGENT_MIN_TOOL_ACCURACY must be at least 0.95")

    return {
        "provider": config.offline_agent_provider,
        "enabled": config.offline_agent_enabled,
        "kill_switch": config.offline_agent_kill_switch,
        "min_device_ram_gb": config.offline_agent_min_device_ram_gb,
        "max_latency_ms": config.offline_agent_max_latency_ms,
        "min_tool_accuracy": config.offline_agent_min_tool_accuracy,
        "ready": not blockers,
        "blockers": blockers,
    }
