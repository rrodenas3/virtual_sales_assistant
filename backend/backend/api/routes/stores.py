from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import OOSAlertPage, PageInfo, StoreDetail
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_store_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/{store_id}", response_model=StoreDetail)
async def store_detail(
    store_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> StoreDetail:
    try:
        store = (
            await osa.get_store_detail(current_user.rep_id, store_id)
            if current_user.role == "rep"
            else await osa.get_store_detail_any(store_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)
    event = await log_audit_event(
        db,
        session_id=f"{current_user.rep_id}:store:{store_id}",
        rep_id=current_user.rep_id,
        event_type="store_detail_read",
        resource_type="store",
        resource_id=store_id,
        payload_json={"store_id": store_id},
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    return store.model_copy(update={"audit_event_id": event.event_id})


@router.get("/{store_id}/alerts", response_model=OOSAlertPage)
async def store_alerts(
    store_id: str,
    min_risk_score: float = Query(default=0.7, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> OOSAlertPage:
    try:
        store = (
            await osa.get_store_detail(current_user.rep_id, store_id)
            if current_user.role == "rep"
            else await osa.get_store_detail_any(store_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)
    alert_rep_id = current_user.rep_id if current_user.role == "rep" else store.rep_id
    alerts, next_cursor = await osa.get_oos_alerts(alert_rep_id, store_id, min_risk_score, limit, cursor)
    event = await log_audit_event(
        db,
        session_id=f"{current_user.rep_id}:alerts:{store_id}",
        rep_id=current_user.rep_id,
        event_type="oos_alerts_read",
        resource_type="store",
        resource_id=store_id,
        payload_json={"count": len(alerts), "min_risk_score": min_risk_score},
        data_freshness_ts=alerts[0].data_freshness_ts if alerts else store.data_freshness_ts,
    )
    await db.commit()
    alerts = [alert.model_copy(update={"audit_event_id": event.event_id}) for alert in alerts]
    return OOSAlertPage(alerts=alerts, page=PageInfo(next_cursor=next_cursor, limit=limit))
