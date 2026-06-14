from dataclasses import dataclass


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
    lowered = text.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lowered:
            return GuardrailResult(True, f"Potential prompt injection detected: {pattern}", 1.0)
    return GuardrailResult(False)

