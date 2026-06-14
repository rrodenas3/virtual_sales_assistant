from typing import Protocol

from backend.api.schemas import AssortmentGap, PromoRecommendation, UpsellOpportunity


class RGMDataPort(Protocol):
    source_system: str
    model_version: str

    async def get_recommendations(
        self,
        store_id: str,
        revenue_opportunity_score: float,
        promo_compliance_rate: float,
    ) -> tuple[list[PromoRecommendation], list[AssortmentGap], list[UpsellOpportunity]]:
        ...


class MockRGMAdapter:
    source_system = "mock"
    model_version = "mock-rgm-v1"

    async def get_recommendations(
        self,
        store_id: str,
        revenue_opportunity_score: float,
        promo_compliance_rate: float,
    ) -> tuple[list[PromoRecommendation], list[AssortmentGap], list[UpsellOpportunity]]:
        confidence = "high" if revenue_opportunity_score >= 0.75 else "medium"
        promos = [
            PromoRecommendation(
                recommendation_id=f"PROMO:{store_id}:SKU-4001",
                store_id=store_id,
                sku_id="SKU-4001",
                promo_name="Weekend endcap recovery",
                expected_lift=round(0.08 + (1 - promo_compliance_rate) * 0.22, 3),
                margin_impact=round(0.03 + revenue_opportunity_score * 0.05, 3),
                reason="Promo compliance gap indicates the display is worth checking before the next weekend peak.",
                confidence_label=confidence,  # type: ignore[arg-type]
            )
        ]
        assortment_gaps = [
            AssortmentGap(
                gap_id=f"GAP:{store_id}:SKU-4004",
                store_id=store_id,
                sku_id="SKU-4004",
                sku_name="Core SKU 4004",
                category="Beverages",
                estimated_revenue_opportunity=round(350 + revenue_opportunity_score * 900, 2),
                reason="Comparable tier stores carry this SKU with stronger velocity.",
                confidence_label=confidence,  # type: ignore[arg-type]
            )
        ]
        upsells = [
            UpsellOpportunity(
                opportunity_id=f"UPSELL:{store_id}:SKU-4002",
                store_id=store_id,
                sku_id="SKU-4002",
                sku_name="Core SKU 4002",
                estimated_value=round(120 + revenue_opportunity_score * 500, 2),
                reason="Recent 30-day revenue and store tier support a small incremental order.",
                confidence_label=confidence,  # type: ignore[arg-type]
            )
        ]
        return promos, assortment_gaps, upsells


rgm_adapter: RGMDataPort = MockRGMAdapter()
