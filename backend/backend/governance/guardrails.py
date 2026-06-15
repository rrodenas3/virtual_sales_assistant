from dataclasses import dataclass
from typing import Protocol

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
        log_structured_event(
            "guardrail_classifier_deferred",
            fail_closed=settings.guardrail_fail_closed,
            endpoint_configured=True,
        )
        if settings.guardrail_fail_closed:
            return GuardrailResult(True, "External guardrail classifier integration is deferred", 1.0)
        return PatternGuardrailProvider().check(text)


def get_guardrail_provider() -> GuardrailProvider:
    if settings.guardrail_provider == "pattern":
        return PatternGuardrailProvider()
    return ExternalClassifierGuardrailProvider()

