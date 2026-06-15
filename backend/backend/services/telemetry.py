import json
import logging
import random
import time
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger("phantom.telemetry")


def log_structured_event(event_name: str, **fields: Any) -> None:
    if settings.observability_provider == "none":
        return
    payload = {
        "event_name": event_name,
        "service_name": settings.otel_service_name,
        "app_env": settings.app_env,
        **fields,
    }
    logger.info(json.dumps(payload, default=str, sort_keys=True))
    if settings.observability_provider == "otlp_http":
        _emit_otlp_log(payload)


def should_sample_trace() -> bool:
    if settings.observability_provider == "none":
        return False
    return random.random() <= settings.trace_sample_rate


def perf_counter_ms() -> float:
    return time.perf_counter() * 1000


def _emit_otlp_log(payload: dict[str, Any]) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        if settings.otel_fail_closed:
            raise RuntimeError("OTEL_EXPORTER_OTLP_ENDPOINT is required when OBSERVABILITY_PROVIDER=otlp_http")
        return
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    if not endpoint.endswith("/v1/logs"):
        endpoint = f"{endpoint}/v1/logs"
    try:
        response = httpx.post(endpoint, json=_otlp_log_payload(payload), timeout=2.0)
        response.raise_for_status()
    except Exception:
        if settings.otel_fail_closed:
            raise


def _otlp_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = str(payload.get("event_name", "event"))
    attributes = [
        {"key": key, "value": _otlp_value(value)}
        for key, value in payload.items()
        if key not in {"event_name", "service_name"}
    ]
    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": str(payload.get("service_name"))}},
                    ],
                },
                "scopeLogs": [
                    {
                        "scope": {"name": "phantom.telemetry"},
                        "logRecords": [
                            {
                                "timeUnixNano": str(time.time_ns()),
                                "severityText": "INFO",
                                "body": {"stringValue": event_name},
                                "attributes": attributes,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _otlp_value(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}
