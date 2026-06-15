from __future__ import annotations

import re
import time
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Protocol

from backend.api.schemas import OOSAlert
from backend.config import settings
from backend.services.summary import build_grounded_summary


class SummaryProviderError(RuntimeError):
    pass


class SummaryGroundingError(ValueError):
    pass


@dataclass(frozen=True)
class SummaryProviderResult:
    summary: str
    provider: str
    model_id: str
    latency_ms: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_eur: float
    fallback_used: bool = False
    grounding_result: str = "passed"


class SummaryProvider(Protocol):
    async def summarize(self, alerts: list[OOSAlert]) -> SummaryProviderResult:
        ...


def summary_provider_status() -> dict:
    blockers: list[str] = []
    anthropic_sdk_available = find_spec("anthropic") is not None
    anthropic_token_configured = bool(settings.anthropic_token_ref)
    provider_ready = settings.summary_provider == "anthropic" and anthropic_token_configured and anthropic_sdk_available

    if settings.summary_provider != "anthropic":
        blockers.append("SUMMARY_PROVIDER must be anthropic for AI-demo readiness")
    if not anthropic_token_configured:
        blockers.append("ANTHROPIC_TOKEN_REF is required for anthropic summaries")
    if not anthropic_sdk_available:
        blockers.append("anthropic SDK is not installed")
    if not settings.ai_demo_eval_validated:
        blockers.append("AI-demo eval must pass with provider=anthropic before AI-demo readiness")

    active_model = settings.anthropic_model if settings.summary_provider == "anthropic" else settings.llm_model_id
    return {
        "selected_provider": settings.summary_provider,
        "active_model": active_model,
        "template_model_id": settings.llm_model_id,
        "anthropic_model": settings.anthropic_model,
        "anthropic_sdk_available": anthropic_sdk_available,
        "anthropic_token_configured": anthropic_token_configured,
        "ai_demo_provider_ready": provider_ready,
        "ai_demo_eval_validated": settings.ai_demo_eval_validated,
        "ai_demo_eval_last_validation_at": settings.ai_demo_eval_last_validation_at,
        "ai_demo_eval_validation_summary": settings.ai_demo_eval_validation_summary,
        "summary_fail_open": settings.summary_fail_open,
        "ai_demo_ready": provider_ready and settings.ai_demo_eval_validated,
        "ai_demo_blockers": blockers,
    }


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_cost_eur(input_tokens: int, output_tokens: int) -> float:
    return round((input_tokens + output_tokens) * 0.000002, 6)


def validate_summary_grounding(summary: str, alerts: list[OOSAlert]) -> None:
    allowed_alert_ids = {alert.alert_id for alert in alerts}
    allowed_sku_ids = {alert.sku_id for alert in alerts}
    allowed_store_ids = {alert.store_id for alert in alerts}

    referenced_alerts = set(re.findall(r"\b[A-Z]{2}-\d{3}:SKU-\d{4}:\d{4}-\d{2}-\d{2}\b", summary))
    referenced_skus = set(re.findall(r"\bSKU-\d{4}\b", summary))
    referenced_stores = set(re.findall(r"\bST-\d{3}\b", summary))

    unknown_alerts = referenced_alerts - allowed_alert_ids
    unknown_skus = referenced_skus - allowed_sku_ids
    unknown_stores = referenced_stores - allowed_store_ids
    if unknown_alerts or unknown_skus or unknown_stores:
        details = {
            "unknown_alert_ids": sorted(unknown_alerts),
            "unknown_sku_ids": sorted(unknown_skus),
            "unknown_store_ids": sorted(unknown_stores),
        }
        raise SummaryGroundingError(f"Summary referenced ungrounded identifiers: {details}")


class TemplateSummaryProvider:
    async def summarize(self, alerts: list[OOSAlert]) -> SummaryProviderResult:
        started = time.perf_counter()
        summary = build_grounded_summary(alerts)
        validate_summary_grounding(summary, alerts)
        input_tokens = _estimate_tokens("".join(alert.model_dump_json() for alert in alerts))
        output_tokens = _estimate_tokens(summary)
        return SummaryProviderResult(
            summary=summary,
            provider="template",
            model_id=settings.llm_model_id,
            latency_ms=round((time.perf_counter() - started) * 1000),
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_eur=_estimate_cost_eur(input_tokens, output_tokens),
        )


class AnthropicSummaryProvider:
    async def summarize(self, alerts: list[OOSAlert]) -> SummaryProviderResult:
        if not settings.anthropic_token_ref:
            raise SummaryProviderError("ANTHROPIC_TOKEN_REF is required when SUMMARY_PROVIDER=anthropic")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise SummaryProviderError("anthropic SDK is not installed") from exc

        prompt = self._prompt(alerts)
        input_tokens = _estimate_tokens(prompt)
        started = time.perf_counter()
        client = AsyncAnthropic(api_key=settings.anthropic_token_ref, timeout=settings.anthropic_timeout_seconds)
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            temperature=0,
            system=(
                "You are PHANTOM, a governed field-sales assistant. "
                "Summarize only the supplied OOS alerts. Do not invent stores, SKUs, alert IDs, or actions."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        summary = "\n".join(text_parts).strip()
        if not summary:
            raise SummaryProviderError("Anthropic summary response was empty")
        validate_summary_grounding(summary, alerts)
        output_tokens = _estimate_tokens(summary)
        usage = getattr(response, "usage", None)
        if usage is not None:
            input_tokens = max(1, int(getattr(usage, "input_tokens", input_tokens) or input_tokens))
            output_tokens = max(1, int(getattr(usage, "output_tokens", output_tokens) or output_tokens))
        return SummaryProviderResult(
            summary=summary,
            provider="anthropic",
            model_id=settings.anthropic_model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_eur=_estimate_cost_eur(input_tokens, output_tokens),
        )

    def _prompt(self, alerts: list[OOSAlert]) -> str:
        if not alerts:
            return "No grounded OOS alerts are available. State that no grounded alerts are available."
        lines = [
            "Create a concise field-sales OSA summary from these grounded alerts only.",
            "Mention the highest-risk issues and recommended actions. Keep it under 160 words.",
            "Grounded alerts:",
        ]
        for alert in sorted(alerts, key=lambda item: (-item.risk_score, item.sku_id)):
            lines.append(
                "- "
                f"alert_id={alert.alert_id}; store_id={alert.store_id}; sku_id={alert.sku_id}; "
                f"sku_name={alert.sku_name}; risk_score={alert.risk_score}; "
                f"phantom_inventory={alert.is_phantom_inventory}; root_cause={alert.root_cause_label}; "
                f"recommended_action={alert.recommended_action}; confidence={alert.confidence_label}"
            )
        return "\n".join(lines)


def get_summary_provider() -> SummaryProvider:
    if settings.summary_provider == "anthropic":
        return AnthropicSummaryProvider()
    return TemplateSummaryProvider()
