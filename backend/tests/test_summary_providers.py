from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.api.schemas import OOSAlert
from backend.config import settings
from backend.services.summary_providers import (
    AnthropicSummaryProvider,
    SummaryGroundingError,
    SummaryProviderError,
    TemplateSummaryProvider,
    get_summary_provider,
)


def _alert() -> OOSAlert:
    return OOSAlert(
        alert_id="ST-001:SKU-4001:2026-06-15",
        prediction_row_id="PRED-1",
        store_id="ST-001",
        sku_id="SKU-4001",
        sku_name="Core SKU 4001",
        category="Beverages",
        risk_score=0.92,
        is_phantom_inventory=True,
        predicted_stockout_date="2026-06-16",
        root_cause_label="phantom",
        recommended_action="Verify backroom inventory; escalate phantom signal",
        confidence_label="high",
        data_freshness_ts=datetime(2026, 6, 15, tzinfo=timezone.utc),
        model_version="mock-v1",
        source_system="mock",
    )


@pytest.mark.asyncio
async def test_template_summary_provider_returns_grounded_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "summary_provider", "template")
    monkeypatch.setattr(settings, "llm_model_id", "grounded-template-v1")

    result = await get_summary_provider().summarize([_alert()])

    assert isinstance(get_summary_provider(), TemplateSummaryProvider)
    assert result.provider == "template"
    assert result.model_id == "grounded-template-v1"
    assert result.grounding_result == "passed"
    assert result.estimated_cost_eur > 0
    assert "Core SKU 4001" in result.summary


@pytest.mark.asyncio
async def test_anthropic_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_token_ref", None)

    with pytest.raises(SummaryProviderError, match="ANTHROPIC_TOKEN_REF"):
        await AnthropicSummaryProvider().summarize([_alert()])


@pytest.mark.asyncio
async def test_anthropic_provider_rejects_ungrounded_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMessages:
        async def create(self, **_: object) -> object:
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Check SKU-9999 at ST-999 immediately.")],
                usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            )

    class FakeAsyncAnthropic:
        def __init__(self, **_: object) -> None:
            self.messages = FakeMessages()

    fake_module = types.ModuleType("anthropic")
    fake_module.AsyncAnthropic = FakeAsyncAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setattr(settings, "anthropic_token_ref", "test-token-ref")
    monkeypatch.setattr(settings, "anthropic_model", "claude-haiku-4-5")

    with pytest.raises(SummaryGroundingError):
        await AnthropicSummaryProvider().summarize([_alert()])


@pytest.mark.asyncio
async def test_anthropic_provider_returns_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMessages:
        async def create(self, **kwargs: object) -> object:
            assert kwargs["model"] == "claude-haiku-4-5"
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="SKU-4001 at ST-001 has a high phantom risk.")],
                usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            )

    class FakeAsyncAnthropic:
        def __init__(self, **_: object) -> None:
            self.messages = FakeMessages()

    fake_module = types.ModuleType("anthropic")
    fake_module.AsyncAnthropic = FakeAsyncAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setattr(settings, "anthropic_token_ref", "test-token-ref")
    monkeypatch.setattr(settings, "anthropic_model", "claude-haiku-4-5")

    result = await AnthropicSummaryProvider().summarize([_alert()])

    assert result.provider == "anthropic"
    assert result.model_id == "claude-haiku-4-5"
    assert result.estimated_input_tokens == 100
    assert result.estimated_output_tokens == 20
