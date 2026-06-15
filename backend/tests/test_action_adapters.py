import httpx
import pytest

from backend.adapters.crm import ExternalCRMAdapter
from backend.adapters.erp import ExternalERPAdapter
from backend.adapters.shelf_image import ExternalShelfImageAdapter
from backend.api.schemas import OOSAlert
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


@pytest.mark.asyncio
async def test_external_shelf_image_adapter_posts_grounded_alerts(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_endpoint", "https://vision.example.test")
    monkeypatch.setattr(settings, "shelf_image_token_ref", "shelf-token-ref")
    monkeypatch.setattr(settings, "shelf_image_timeout_seconds", 3.0)
    _mock_async_client(
        monkeypatch,
        {
            "analysis_id": "analysis-1",
            "model_version": "vision-v1",
            "findings": [
                {
                    "finding_id": "finding-1",
                    "store_id": "ST-001",
                    "sku_id": "SKU-4001",
                    "finding_type": "possible_oos",
                    "confidence_label": "medium",
                    "evidence": "External provider returned a grounded finding.",
                    "recommended_action": "Confirm on-shelf availability",
                    "grounded_alert_id": "ST-001:SKU-4001:2026-06-15",
                }
            ],
        },
    )
    alert = OOSAlert(
        alert_id="ST-001:SKU-4001:2026-06-15",
        prediction_row_id="PRED-1",
        store_id="ST-001",
        sku_id="SKU-4001",
        sku_name="Core SKU 4001",
        category="Beverages",
        risk_score=0.8,
        is_phantom_inventory=False,
        predicted_stockout_date=None,
        root_cause_label="low_inventory",
        recommended_action="Confirm on-shelf availability",
        confidence_label="medium",
        data_freshness_ts="2026-06-15T00:00:00Z",
        model_version="mock-v1",
        source_system="mock",
    )

    analysis_id, findings = await ExternalShelfImageAdapter(settings).analyze(
        store_id="ST-001",
        image_ref="upload://session/image-1",
        alerts=[alert],
    )

    assert analysis_id == "analysis-1"
    assert findings[0].grounded_alert_id == alert.alert_id


def test_external_shelf_image_adapter_requires_endpoint_and_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_endpoint", None)
    monkeypatch.setattr(settings, "shelf_image_token_ref", None)

    with pytest.raises(RuntimeError, match="shelf_image_endpoint, shelf_image_token_ref"):
        ExternalShelfImageAdapter(settings)
