import json
import logging
from typing import Any

logger = logging.getLogger("phantom.telemetry")


def log_structured_event(event_name: str, **fields: Any) -> None:
    logger.info(json.dumps({"event_name": event_name, **fields}, default=str, sort_keys=True))
