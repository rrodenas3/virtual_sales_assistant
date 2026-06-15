import pytest
import httpx

from backend.config import settings
from backend.memory import adapters
from backend.memory.adapters import Mem0Adapter, NullMemoryAdapter, get_memory_adapter


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
    monkeypatch.setattr(settings, "discovery_memory_retention_policy", "30 days")
    monkeypatch.setattr(settings, "discovery_memory_scopes", "rep,store,session")
    monkeypatch.setattr(settings, "mem0_token_ref", None)
    with pytest.raises(RuntimeError, match="mem0_token_ref"):
        get_memory_adapter()


def test_mem0_adapter_is_blocked_by_discovery(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_provider", "mem0")
    monkeypatch.setattr(settings, "discovery_memory_retention_policy", None)
    monkeypatch.setattr(settings, "discovery_memory_scopes", None)
    monkeypatch.setattr(settings, "mem0_token_ref", "token-ref")

    with pytest.raises(RuntimeError, match="discovery_memory_retention_policy"):
        get_memory_adapter()


def _mock_mem0(monkeypatch, responses: list[dict]) -> list[dict]:
    real_client = httpx.AsyncClient
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append({"url": str(request.url), "body": request.content.decode()})
        payload = responses.pop(0)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    def client_factory(*, timeout: float) -> httpx.AsyncClient:
        return real_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(adapters.httpx, "AsyncClient", client_factory)
    return requests


@pytest.mark.asyncio
async def test_mem0_adapter_reads_and_writes_scoped_memory(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_provider", "mem0")
    monkeypatch.setattr(settings, "discovery_memory_retention_policy", "30 days")
    monkeypatch.setattr(settings, "discovery_memory_scopes", "rep,store,session")
    monkeypatch.setattr(settings, "mem0_token_ref", "mem0-token-ref")
    monkeypatch.setattr(settings, "mem0_endpoint", "https://mem0.example.test")
    requests = _mock_mem0(
        monkeypatch,
        [
            {"memories": [{"id": "mem-1", "memory": "Store has back-room inventory issues"}]},
            {"id": "write-1"},
        ],
    )
    adapter = Mem0Adapter()

    context = await adapter.get_context(rep_id="REP-001", store_id="ST-001")
    await adapter.record_interaction(
        rep_id="REP-001",
        session_id="session-1",
        payload={"event_type": "osa_summary_created", "store_id": "ST-001", "summary": "Grounded summary"},
    )

    assert context["provider"] == "mem0"
    assert context["memories"][0]["id"] == "mem-1"
    assert requests[0]["url"] == "https://mem0.example.test/memories/search"
    assert requests[1]["url"] == "https://mem0.example.test/memories"
    assert "REP-001" in requests[0]["body"]
    assert "ST-001" in requests[1]["body"]
