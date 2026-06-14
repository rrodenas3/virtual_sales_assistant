from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import VisitPriority
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_territory_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("/today", response_model=list[VisitPriority])
async def today_visits(
    territory_code: str,
    date_: date | None = Query(default=None, alias="date"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> list[VisitPriority]:
    assert_territory_access(current_user, territory_code)
    visit_date = date_ or date.today()
    visits = await osa.get_visit_priority(current_user.rep_id, territory_code, visit_date)
    event = await log_audit_event(
        db,
        session_id=f"{current_user.rep_id}:{visit_date.isoformat()}",
        rep_id=current_user.rep_id,
        event_type="visit_priority_read",
        resource_type="territory",
        resource_id=territory_code,
        payload_json={"count": len(visits), "formula_version": "priority-v1"},
        data_freshness_ts=visits[0].data_freshness_ts if visits else None,
    )
    await db.commit()
    return [visit.model_copy(update={"audit_event_ids": [event.event_id]}) for visit in visits]
