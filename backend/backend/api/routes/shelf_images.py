from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.adapters.shelf_image import ShelfImagePort
from backend.api.schemas import ShelfImageAnalysisRequest, ShelfImageAnalysisResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_osa_adapter, get_shelf_image_adapter
from backend.governance.rbac import assert_store_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/stores", tags=["shelf-images"])


@router.post("/{store_id}/shelf-image-analysis", response_model=ShelfImageAnalysisResponse)
async def analyze_shelf_image(
    store_id: str,
    request: ShelfImageAnalysisRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
    shelf_images: ShelfImagePort = Depends(get_shelf_image_adapter),
) -> ShelfImageAnalysisResponse:
    if request.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="store_id path/body mismatch")
    try:
        store = (
            await osa.get_store_detail(current_user.rep_id, store_id)
            if current_user.role == "rep"
            else await osa.get_store_detail_any(store_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)

    alerts = await osa.get_alerts_by_ids(current_user.rep_id, store.territory_code, request.alert_ids)
    if request.alert_ids is not None and len(alerts) != len(set(request.alert_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown alert_id in grounded set")
    alerts = [alert for alert in alerts if alert.store_id == store_id]

    analysis_id, findings = await shelf_images.analyze(
        store_id=store_id,
        image_ref=request.image_ref,
        alerts=alerts,
    )
    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="shelf_image_analysis_created",
        resource_type="store",
        resource_id=store_id,
        payload_json={
            "analysis_id": analysis_id,
            "image_ref": request.image_ref,
            "grounded_alert_ids": [alert.alert_id for alert in alerts],
            "finding_count": len(findings),
            "model_version": shelf_images.model_version,
        },
        source_system=shelf_images.source_system,
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    return ShelfImageAnalysisResponse(
        analysis_id=analysis_id,
        store_id=store_id,
        findings=findings,
        source_system=shelf_images.source_system,
        model_version=shelf_images.model_version,
        audit_event_id=event.event_id,
    )
