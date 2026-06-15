from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.config import settings
from backend.services.telemetry import log_structured_event


BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "disregard your",
    "forget your guidelines",
    "act as if you",
    "pretend you are",
]


@dataclass(frozen=True)
class GuardrailResult:
    blocked: bool
    reason: str | None = None
    risk_score: float = 0.0


def check_guardrails(text: str) -> GuardrailResult:
    return get_guardrail_provider().check(text)


def guardrail_status() -> dict:
    blockers: list[str] = []
    if settings.guardrail_provider == "external_classifier" and not settings.guardrail_classifier_endpoint:
        blockers.append("GUARDRAIL_CLASSIFIER_ENDPOINT is required for external classifier mode")
    return {
        "provider": settings.guardrail_provider,
        "classifier_endpoint_configured": bool(settings.guardrail_classifier_endpoint),
        "block_threshold": settings.guardrail_classifier_block_threshold,
        "timeout_seconds": settings.guardrail_classifier_timeout_seconds,
        "fail_closed": settings.guardrail_fail_closed,
        "ready": not blockers,
        "blockers": blockers,
    }


class GuardrailProvider(Protocol):
    def check(self, text: str) -> GuardrailResult:
        ...


class PatternGuardrailProvider:
    def check(self, text: str) -> GuardrailResult:
        lowered = text.lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in lowered:
                return GuardrailResult(True, f"Potential prompt injection detected: {pattern}", 1.0)
        return GuardrailResult(False)


class ExternalClassifierGuardrailProvider:
    def check(self, text: str) -> GuardrailResult:
        if not settings.guardrail_classifier_endpoint:
            log_structured_event(
                "guardrail_classifier_unavailable",
                fail_closed=settings.guardrail_fail_closed,
                provider=settings.guardrail_provider,
            )
            if settings.guardrail_fail_closed:
                return GuardrailResult(True, "External guardrail classifier is not configured", 1.0)
            return PatternGuardrailProvider().check(text)
        try:
            with httpx.Client(timeout=settings.guardrail_classifier_timeout_seconds) as client:
                response = client.post(settings.guardrail_classifier_endpoint, json={"text": text})
                response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            log_structured_event(
                "guardrail_classifier_failed",
                fail_closed=settings.guardrail_fail_closed,
                error_type=type(exc).__name__,
                block_threshold=settings.guardrail_classifier_block_threshold,
            )
            if settings.guardrail_fail_closed:
                return GuardrailResult(True, "External guardrail classifier failed", 1.0)
            return PatternGuardrailProvider().check(text)

        risk_score = float(body.get("risk_score", 0.0))
        blocked = bool(body.get("blocked", False)) or risk_score >= settings.guardrail_classifier_block_threshold
        reason = body.get("reason") or (
            f"External guardrail classifier risk {risk_score:.2f}"
            if blocked
            else None
        )
        log_structured_event(
            "guardrail_classifier_checked",
            blocked=blocked,
            risk_score=risk_score,
            block_threshold=settings.guardrail_classifier_block_threshold,
        )
        return GuardrailResult(blocked=blocked, reason=reason, risk_score=risk_score)


def get_guardrail_provider() -> GuardrailProvider:
    if settings.guardrail_provider == "pattern":
        return PatternGuardrailProvider()
    return ExternalClassifierGuardrailProvider()

