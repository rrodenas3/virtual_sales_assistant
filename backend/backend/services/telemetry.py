import json
import logging
import random
import time
from typing import Any

from backend.config import settings

logger = logging.getLogger("phantom.telemetry")


def log_structured_event(event_name: str, **fields: Any) -> None:
    if settings.observability_provider == "none":
        return
    logger.info(json.dumps({"event_name": event_name, **fields}, default=str, sort_keys=True))


def should_sample_trace() -> bool:
    if settings.observability_provider == "none":
        return False
    return random.random() <= settings.trace_sample_rate


def perf_counter_ms() -> float:
    return time.perf_counter() * 1000
