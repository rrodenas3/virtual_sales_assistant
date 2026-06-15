import httpx
import pytest

from backend.adapters.crm import ExternalCRMAdapter
from backend.adapters.erp import ExternalERPAdapter
from backend.config import settings


def _mock_async_client(monkeypatch, payload: dict, status_code: int = 200) -> None:
    real_client = httpx.AsyncClient

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    transport = httpx.MockTransport(handler)

    def client_factory(*, timeout: float) -> httpx.AsyncClient:
        return real_client(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)


@pytest.mark.asyncio
async def test_external_crm_adapter_posts_visit_log(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_endpoint", "https://crm.example.test")
    monkeypatch.setattr(settings, "crm_token_ref", "crm-token-ref")
    _mock_async_client(monkeypatch, {"external_id": "visit-123", "status": "SUBMITTED"})

    result = await ExternalCRMAdapter(settings).submit_visit_log({"store_id": "ST-001"})

    assert result.external_id == "visit-123"
    assert result.status == "SUBMITTED"


@pytest.mark.asyncio
async def test_external_erp_adapter_posts_approved_order(monkeypatch) -> None:
    monkeypatch.setattr(settings, "erp_endpoint", "https://erp.example.test")
    monkeypatch.setattr(settings, "erp_token_ref", "erp-token-ref")
    _mock_async_client(monkeypatch, {"erp_order_id": "ERP-123", "status": "ACCEPTED"})

    result = await ExternalERPAdapter(settings).submit_order(
        "draft-1",
        {"items": [{"sku_id": "SKU-4001"}]},
        "approval-1",
        "hash-1",
    )

    assert result.erp_order_id == "ERP-123"
    assert result.status == "ACCEPTED"


def test_external_crm_adapter_requires_endpoint_and_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_endpoint", None)
    monkeypatch.setattr(settings, "crm_token_ref", None)

    with pytest.raises(RuntimeError, match="crm_endpoint, crm_token_ref"):
        ExternalCRMAdapter(settings)


def test_external_erp_adapter_requires_endpoint_and_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "erp_endpoint", None)
    monkeypatch.setattr(settings, "erp_token_ref", None)

    with pytest.raises(RuntimeError, match="erp_endpoint, erp_token_ref"):
        ExternalERPAdapter(settings)
