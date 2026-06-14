from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.adapters.rgm import RGMDataPort
from backend.api.schemas import RGMRecommendationsResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_osa_adapter, get_rgm_adapter
from backend.governance.rbac import assert_store_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/stores", tags=["rgm"])


@router.get("/{store_id}/rgm-recommendations", response_model=RGMRecommendationsResponse)
async def rgm_recommendations(
    store_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
    rgm: RGMDataPort = Depends(get_rgm_adapter),
) -> RGMRecommendationsResponse:
    try:
        store = (
            await osa.get_store_detail(current_user.rep_id, store_id)
            if current_user.role == "rep"
            else await osa.get_store_detail_any(store_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)

    promos, gaps, upsells = await rgm.get_recommendations(
        store_id,
        store.revenue_opportunity_score,
        store.promo_compliance_rate,
    )
    event = await log_audit_event(
        db,
        session_id=f"{current_user.rep_id}:rgm:{store_id}",
        rep_id=current_user.rep_id,
        event_type="rgm_recommendations_read",
        resource_type="store",
        resource_id=store_id,
        payload_json={"promos": len(promos), "assortment_gaps": len(gaps), "upsells": len(upsells)},
        source_system=rgm.source_system,
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    return RGMRecommendationsResponse(
        store_id=store_id,
        promos=promos,
        assortment_gaps=gaps,
        upsell_opportunities=upsells,
        source_system=rgm.source_system,
        model_version=rgm.model_version,
        audit_event_id=event.event_id,
    )
