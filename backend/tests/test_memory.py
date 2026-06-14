import pytest

from backend.config import settings
from backend.memory.adapters import NullMemoryAdapter, get_memory_adapter


@pytest.mark.asyncio
async def test_null_memory_adapter_is_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_provider", "none")
    adapter = get_memory_adapter()
    assert isinstance(adapter, NullMemoryAdapter)
    context = await adapter.get_context(rep_id="REP-001", store_id="ST-001")
    assert context["memories"] == []
    await adapter.record_interaction(rep_id="REP-001", session_id="s1", payload={"event": "read"})


def test_mem0_adapter_fails_closed_without_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_provider", "mem0")
    monkeypatch.setattr(settings, "mem0_token_ref", None)
    with pytest.raises(RuntimeError, match="mem0_token_ref"):
        get_memory_adapter()
