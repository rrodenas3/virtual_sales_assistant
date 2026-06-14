from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from backend.api.schemas import OOSAlert, StoreDetail, TerritoryStoreSummary, VisitComponents, VisitPriority
from backend.config import settings
from backend.services.rules import action_and_confidence, priority_reasons


@dataclass(frozen=True)
class StoreSeed:
    store_id: str
    store_name: str
    retailer_name: str
    address: str
    store_tier: str
    territory_code: str
    rep_id: str
    last_visit_date: date | None
    next_visit_date: date | None
    units_sold_30d: int
    revenue_30d: float
    promo_compliance_rate: float
    revenue_opportunity_score: float
    data_freshness_ts: datetime


@dataclass(frozen=True)
class AlertSeed:
    prediction_row_id: str
    store_id: str
    sku_id: str
    sku_name: str
    category: str
    risk_score: float
    is_phantom_inventory: bool
    predicted_stockout_date: date | None
    root_cause_label: str
    data_freshness_ts: datetime

    @property
    def alert_id(self) -> str:
        prediction_date = self.data_freshness_ts.date().isoformat()
        return f"{self.store_id}:{self.sku_id}:{prediction_date}"


class OSADataPort(Protocol):
    async def get_visit_priority(self, rep_id: str, territory_code: str, visit_date: date) -> list[VisitPriority]:
        ...

    async def get_oos_alerts(
        self,
        rep_id: str,
        store_id: str,
        min_risk_score: float,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[OOSAlert], str | None]:
        ...

    async def get_store_detail(self, rep_id: str, store_id: str) -> StoreDetail:
        ...

    async def get_alerts_by_ids(self, rep_id: str, territory_code: str, alert_ids: list[str] | None) -> list[OOSAlert]:
        ...

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        ...

    async def get_territory_store_summaries(self, territory_code: str, visit_date: date) -> list[TerritoryStoreSummary]:
        ...


def _fresh(days_old: int = 0) -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=days_old)


class MockOSAAdapter:
    source_system = settings.osa_source_system
    model_version = settings.osa_model_version

    def __init__(self) -> None:
        today = date.today()
        self.stores = self._build_stores(today)
        self.alerts = self._build_alerts(today)

    def _build_stores(self, today: date) -> list[StoreSeed]:
        stores: list[StoreSeed] = []
        for i in range(1, 26):
            rep_number = ((i - 1) % 5) + 1
            tier = ["A", "B", "C"][i % 3]
            stores.append(
                StoreSeed(
                    store_id=f"ST-{i:03d}",
                    store_name=f"West Market {i:02d}",
                    retailer_name="Northstar Retail",
                    address=f"{100 + i} Commerce Ave, West District",
                    store_tier=tier,
                    territory_code="WEST-01",
                    rep_id=f"REP-{rep_number:03d}",
                    last_visit_date=today - timedelta(days=(i * 3) % 35),
                    next_visit_date=today + timedelta(days=i % 7),
                    units_sold_30d=900 + i * 77,
                    revenue_30d=12500 + i * 925,
                    promo_compliance_rate=max(0.35, min(0.98, 0.95 - (i % 8) * 0.07)),
                    revenue_opportunity_score=max(0.2, min(0.95, 0.35 + (i % 9) * 0.07)),
                    data_freshness_ts=_fresh(i % 2),
                )
            )
        return stores

    def _build_alerts(self, today: date) -> list[AlertSeed]:
        categories = ["Beverages", "Snacks", "Dairy", "Household", "Personal Care"]
        causes = ["phantom", "distributor_delay", "promotion_spike", "unexpected_velocity"]
        alerts: list[AlertSeed] = []
        row = 1
        for store_index in range(1, 26):
            for sku_index in range(1, 6):
                risk = round(0.7 + ((store_index * sku_index) % 29) / 100, 2)
                alerts.append(
                    AlertSeed(
                        prediction_row_id=f"PRED-{row:05d}",
                        store_id=f"ST-{store_index:03d}",
                        sku_id=f"SKU-{4000 + sku_index:04d}",
                        sku_name=f"Core SKU {4000 + sku_index}",
                        category=categories[(store_index + sku_index) % len(categories)],
                        risk_score=risk,
                        is_phantom_inventory=(store_index + sku_index) % 5 == 0,
                        predicted_stockout_date=today + timedelta(days=(sku_index % 4) + 1),
                        root_cause_label=causes[(store_index + sku_index) % len(causes)],
                        data_freshness_ts=_fresh(2 if store_index % 13 == 0 else 0),
                    )
                )
                row += 1
        return alerts

    def _store_for_rep(self, rep_id: str, store_id: str) -> StoreSeed | None:
        return next((s for s in self.stores if s.store_id == store_id and s.rep_id == rep_id), None)

    def _store_by_id(self, store_id: str) -> StoreSeed | None:
        return next((s for s in self.stores if s.store_id == store_id), None)

    async def get_visit_priority(self, rep_id: str, territory_code: str, visit_date: date) -> list[VisitPriority]:
        rows: list[VisitPriority] = []
        for store in [s for s in self.stores if s.rep_id == rep_id and s.territory_code == territory_code]:
            store_alerts = [a for a in self.alerts if a.store_id == store.store_id and a.risk_score >= 0.7]
            avg_oos = round(sum(a.risk_score for a in store_alerts) / len(store_alerts), 3) if store_alerts else 0.0
            days_since = (visit_date - store.last_visit_date).days if store.last_visit_date else 30
            recency = min(max(days_since, 0) / 30, 1.0)
            components = VisitComponents(
                oos_risk=avg_oos,
                promo_gap=round(1 - store.promo_compliance_rate, 3),
                revenue_opportunity=store.revenue_opportunity_score,
                visit_recency=round(recency, 3),
            )
            score = round(
                0.4 * components.oos_risk
                + 0.3 * components.promo_gap
                + 0.2 * components.revenue_opportunity
                + 0.1 * components.visit_recency,
                3,
            )
            rows.append(
                VisitPriority(
                    store_id=store.store_id,
                    store_name=store.store_name,
                    address=store.address,
                    priority_score=score,
                    rank=0,
                    reasons=priority_reasons(
                        avg_oos_risk_score=avg_oos,
                        promo_compliance_rate=store.promo_compliance_rate,
                        revenue_opportunity_score=store.revenue_opportunity_score,
                        days_since_last_visit=days_since,
                        oos_sku_count=len(store_alerts),
                    ),
                    components=components,
                    oos_sku_count=len(store_alerts),
                    data_freshness_ts=store.data_freshness_ts,
                )
            )
        rows.sort(key=lambda r: (-r.priority_score, -r.oos_sku_count, r.store_id))
        return [row.model_copy(update={"rank": idx + 1}) for idx, row in enumerate(rows)]

    async def get_oos_alerts(
        self,
        rep_id: str,
        store_id: str,
        min_risk_score: float,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[OOSAlert], str | None]:
        if not self._store_for_rep(rep_id, store_id):
            return [], None
        offset = int(cursor or "0")
        filtered = [
            alert for alert in self.alerts if alert.store_id == store_id and alert.risk_score >= min_risk_score
        ]
        filtered.sort(key=lambda alert: (-alert.risk_score, alert.sku_id))
        page = filtered[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(filtered) else None
        return [self._to_alert(alert) for alert in page], next_cursor

    async def get_store_detail(self, rep_id: str, store_id: str) -> StoreDetail:
        store = self._store_for_rep(rep_id, store_id)
        if not store:
            raise KeyError(store_id)
        return self._to_store_detail(store)

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        store = self._store_by_id(store_id)
        if not store:
            raise KeyError(store_id)
        return self._to_store_detail(store)

    async def get_territory_store_summaries(self, territory_code: str, visit_date: date) -> list[TerritoryStoreSummary]:
        summaries: list[TerritoryStoreSummary] = []
        for store in [s for s in self.stores if s.territory_code == territory_code]:
            priorities = await self.get_visit_priority(store.rep_id, territory_code, visit_date)
            priority = next((row for row in priorities if row.store_id == store.store_id), None)
            oos_count = len([a for a in self.alerts if a.store_id == store.store_id and a.risk_score >= 0.7])
            summaries.append(
                TerritoryStoreSummary(
                    store_id=store.store_id,
                    store_name=store.store_name,
                    rep_id=store.rep_id,
                    priority_score=priority.priority_score if priority else 0.0,
                    oos_sku_count=oos_count,
                    confirmed_feedback_count=0,
                    false_positive_count=0,
                    open_draft_count=0,
                    data_freshness_ts=store.data_freshness_ts,
                )
            )
        summaries.sort(key=lambda row: (-row.priority_score, -row.oos_sku_count, row.store_id))
        return summaries

    def _to_store_detail(self, store: StoreSeed) -> StoreDetail:
        oos_count = len([a for a in self.alerts if a.store_id == store.store_id and a.risk_score >= 0.7])
        return StoreDetail(
            store_id=store.store_id,
            store_name=store.store_name,
            retailer_name=store.retailer_name,
            address=store.address,
            store_tier=store.store_tier,  # type: ignore[arg-type]
            territory_code=store.territory_code,
            rep_id=store.rep_id,
            last_visit_date=store.last_visit_date.isoformat() if store.last_visit_date else None,
            next_visit_date=store.next_visit_date.isoformat() if store.next_visit_date else None,
            units_sold_30d=store.units_sold_30d,
            revenue_30d=store.revenue_30d,
            promo_compliance_rate=store.promo_compliance_rate,
            revenue_opportunity_score=store.revenue_opportunity_score,
            oos_sku_count=oos_count,
            data_freshness_ts=store.data_freshness_ts,
        )

    async def get_alerts_by_ids(self, rep_id: str, territory_code: str, alert_ids: list[str] | None) -> list[OOSAlert]:
        rep_store_ids = {
            store.store_id for store in self.stores if store.rep_id == rep_id and store.territory_code == territory_code
        }
        alerts = [alert for alert in self.alerts if alert.store_id in rep_store_ids]
        if alert_ids is not None:
            wanted = set(alert_ids)
            alerts = [alert for alert in alerts if alert.alert_id in wanted]
        return [self._to_alert(alert) for alert in alerts if alert.risk_score >= 0.7]

    def _to_alert(self, seed: AlertSeed) -> OOSAlert:
        recommended_action, confidence_label = action_and_confidence(
            risk_score=seed.risk_score,
            is_phantom_inventory=seed.is_phantom_inventory,
            data_freshness_ts=seed.data_freshness_ts,
        )
        return OOSAlert(
            alert_id=seed.alert_id,
            prediction_row_id=seed.prediction_row_id,
            store_id=seed.store_id,
            sku_id=seed.sku_id,
            sku_name=seed.sku_name,
            category=seed.category,
            risk_score=seed.risk_score,
            is_phantom_inventory=seed.is_phantom_inventory,
            predicted_stockout_date=seed.predicted_stockout_date.isoformat() if seed.predicted_stockout_date else None,
            root_cause_label=seed.root_cause_label,
            recommended_action=recommended_action,
            confidence_label=confidence_label,
            data_freshness_ts=seed.data_freshness_ts,
            model_version=self.model_version,
            source_system=self.source_system,
        )


osa_adapter: OSADataPort = MockOSAAdapter()
