from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from backend.api.schemas import OOSAlert, VisitPriority


class HITLState(BaseModel):
    required: bool = False
    reason: str | None = None
    resume_token: str | None = None


class AgentState(BaseModel):
    session_id: str
    rep_id: str
    role: Literal["rep", "manager", "admin"] = "rep"
    territory_code: str
    visit_date: date | None = None
    store_id: str | None = None
    alert_ids: list[str] | None = None
    visits: list[VisitPriority] = Field(default_factory=list)
    alerts: list[OOSAlert] = Field(default_factory=list)
    summary: str | None = None
    hitl: HITLState = Field(default_factory=HITLState)
