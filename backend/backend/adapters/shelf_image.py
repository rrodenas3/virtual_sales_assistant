from __future__ import annotations

from typing import Protocol
from uuid import uuid5, NAMESPACE_URL

import httpx

from backend.api.schemas import OOSAlert, ShelfImageFinding
from backend.config import Settings


class ShelfImagePort(Protocol):
    source_system: str
    model_version: str

    async def analyze(
        self,
        *,
        store_id: str,
        image_ref: str,
        alerts: list[OOSAlert],
    ) -> tuple[str, list[ShelfImageFinding]]:
        ...


def _analysis_id(store_id: str, image_ref: str) -> str:
    return f"shelf-{uuid5(NAMESPACE_URL, f'{store_id}:{image_ref}')}"


class MockShelfImageAdapter:
    source_system = "mock"
    model_version = "mock-shelf-v1"

    async def analyze(
        self,
        *,
        store_id: str,
        image_ref: str,
        alerts: list[OOSAlert],
    ) -> tuple[str, list[ShelfImageFinding]]:
        findings: list[ShelfImageFinding] = []
        for alert in sorted(alerts, key=lambda item: (-item.risk_score, item.sku_id))[:3]:
            finding_type = "phantom_inventory_signal" if alert.is_phantom_inventory else "possible_oos"
            findings.append(
                ShelfImageFinding(
                    finding_id=f"{alert.alert_id}:shelf",
                    store_id=store_id,
                    sku_id=alert.sku_id,
                    finding_type=finding_type,
                    confidence_label=alert.confidence_label,
                    evidence="Mock shelf analysis is grounded to the supplied OOS alert set; no image pixels inspected.",
                    recommended_action=alert.recommended_action,
                    grounded_alert_id=alert.alert_id,
                )
            )
        if not findings:
            findings.append(
                ShelfImageFinding(
                    finding_id=f"{store_id}:shelf:no-grounded-alerts",
                    store_id=store_id,
                    sku_id=None,
                    finding_type="unknown",
                    confidence_label="low",
                    evidence="No grounded OOS alerts were supplied for shelf-image comparison.",
                    recommended_action="Capture image for manual review only; do not create replenishment actions from image alone.",
                    grounded_alert_id=None,
                )
            )
        return _analysis_id(store_id, image_ref), findings


class ExternalShelfImageAdapter:
    source_system = "external_shelf_image"

    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in {
                "shelf_image_endpoint": settings.shelf_image_endpoint,
                "shelf_image_token_ref": settings.shelf_image_token_ref,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"External shelf-image adapter missing settings: {', '.join(missing)}")
        self.endpoint = str(settings.shelf_image_endpoint).rstrip("/")
        self.token_ref = str(settings.shelf_image_token_ref)
        self.timeout = settings.shelf_image_timeout_seconds
        self.model_version = "external-shelf-image"

    async def analyze(
        self,
        *,
        store_id: str,
        image_ref: str,
        alerts: list[OOSAlert],
    ) -> tuple[str, list[ShelfImageFinding]]:
        payload = {
            "store_id": store_id,
            "image_ref": image_ref,
            "grounded_alerts": [alert.model_dump(mode="json") for alert in alerts],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.endpoint}/shelf-image/analyze",
                headers={"Authorization": f"Bearer {self.token_ref}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        findings = [ShelfImageFinding.model_validate(row) for row in body.get("findings", [])]
        self.model_version = str(body.get("model_version") or self.model_version)
        return str(body.get("analysis_id") or _analysis_id(store_id, image_ref)), findings
