from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.responses import APIResponse
from app.modules.reporting.application.schemas import (
    ExpiringBatchRow,
    InventoryValueByCategoryOutput,
    InventoryValueOutput,
    LowStockRow,
    MonthlySalesRow,
    MonthlyPurchasingRow,
    PurchasingSummaryOutput,
    SalesByChannelOutput,
    SalesSummaryOutput,
    SalesVsPurchasingRow,
    TopConsumedIngredientRow,
    WasteCostByCategoryOutput,
    WasteCostSummaryOutput,
)
from app.modules.reporting.application.service import (
    CrossModuleReportService,
    InventoryReportService,
    PurchasingReportService,
    SalesReportService,
    WasteReportService,
    _months_ago,
)

router = APIRouter(tags=["Reports"])


def _default_period_start() -> date:
    return date.today() - timedelta(days=30)


def _default_period_end() -> date:
    return date.today()


# ── Dependencies ──────────────────────────────────────────────────────────────

def get_sales_svc(session: Annotated[AsyncSession, Depends(get_session)]) -> SalesReportService:
    return SalesReportService(session)


def get_purchasing_svc(session: Annotated[AsyncSession, Depends(get_session)]) -> PurchasingReportService:
    return PurchasingReportService(session)


def get_inventory_svc(session: Annotated[AsyncSession, Depends(get_session)]) -> InventoryReportService:
    return InventoryReportService(session)


def get_waste_svc(session: Annotated[AsyncSession, Depends(get_session)]) -> WasteReportService:
    return WasteReportService(session)


def get_cross_svc(session: Annotated[AsyncSession, Depends(get_session)]) -> CrossModuleReportService:
    return CrossModuleReportService(session)


# ── Sales reports ─────────────────────────────────────────────────────────────

@router.get("/sales/summary", response_model=APIResponse[SalesSummaryOutput])
async def sales_summary(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    svc: SalesReportService = Depends(get_sales_svc),
) -> APIResponse[SalesSummaryOutput]:
    """Total orders, revenue, delivered vs cancelled counts for the period."""
    return APIResponse(data=await svc.summary(from_date, to_date))


@router.get("/sales/by-channel", response_model=APIResponse[SalesByChannelOutput])
async def sales_by_channel(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    svc: SalesReportService = Depends(get_sales_svc),
) -> APIResponse[SalesByChannelOutput]:
    """Revenue split by sales channel with percentage share."""
    return APIResponse(data=await svc.by_channel(from_date, to_date))


@router.get("/sales/monthly-trend", response_model=APIResponse[list[MonthlySalesRow]])
async def sales_monthly_trend(
    months: int = Query(default=7, ge=1, le=24),
    svc: SalesReportService = Depends(get_sales_svc),
) -> APIResponse[list[MonthlySalesRow]]:
    """Month-by-month revenue and order count for the last N months."""
    return APIResponse(data=await svc.monthly_trend(months))


# ── Purchasing reports ────────────────────────────────────────────────────────

@router.get("/purchasing/summary", response_model=APIResponse[PurchasingSummaryOutput])
async def purchasing_summary(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    svc: PurchasingReportService = Depends(get_purchasing_svc),
) -> APIResponse[PurchasingSummaryOutput]:
    """Total spend, order counts, and average order value for the period."""
    return APIResponse(data=await svc.summary(from_date, to_date))


@router.get("/purchasing/monthly-trend", response_model=APIResponse[list[MonthlyPurchasingRow]])
async def purchasing_monthly_trend(
    months: int = Query(default=7, ge=1, le=24),
    svc: PurchasingReportService = Depends(get_purchasing_svc),
) -> APIResponse[list[MonthlyPurchasingRow]]:
    """Month-by-month purchasing spend for the last N months."""
    return APIResponse(data=await svc.monthly_trend(months))


# ── Inventory reports ─────────────────────────────────────────────────────────

@router.get("/inventory/value", response_model=APIResponse[InventoryValueOutput])
async def inventory_value(
    location_id: UUID | None = Query(default=None),
    svc: InventoryReportService = Depends(get_inventory_svc),
) -> APIResponse[InventoryValueOutput]:
    """
    Current stock value (quantity × last kardex unit cost) per ingredient per location.
    Optionally filtered to a single location.
    """
    return APIResponse(data=await svc.inventory_value(location_id))


@router.get(
    "/inventory/value-by-category",
    response_model=APIResponse[InventoryValueByCategoryOutput],
)
async def inventory_value_by_category(
    svc: InventoryReportService = Depends(get_inventory_svc),
) -> APIResponse[InventoryValueByCategoryOutput]:
    """Total inventory value grouped by ingredient category."""
    return APIResponse(data=await svc.inventory_value_by_category())


@router.get("/inventory/low-stock", response_model=APIResponse[list[LowStockRow]])
async def low_stock(
    svc: InventoryReportService = Depends(get_inventory_svc),
) -> APIResponse[list[LowStockRow]]:
    """Ingredients at or below their reorder point, sorted by shortfall descending."""
    return APIResponse(data=await svc.low_stock())


@router.get("/inventory/expiring-soon", response_model=APIResponse[list[ExpiringBatchRow]])
async def expiring_soon(
    days: int = Query(default=7, ge=1, le=90),
    svc: InventoryReportService = Depends(get_inventory_svc),
) -> APIResponse[list[ExpiringBatchRow]]:
    """Batches expiring within the next N days, sorted by expiry date ascending."""
    return APIResponse(data=await svc.expiring_soon(days))


# ── Waste reports ─────────────────────────────────────────────────────────────

@router.get("/waste/summary", response_model=APIResponse[WasteCostSummaryOutput])
async def waste_summary(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    svc: WasteReportService = Depends(get_waste_svc),
) -> APIResponse[WasteCostSummaryOutput]:
    """Total waste quantity and cost for the period."""
    return APIResponse(data=await svc.summary(from_date, to_date))


@router.get("/waste/by-category", response_model=APIResponse[WasteCostByCategoryOutput])
async def waste_by_category(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    svc: WasteReportService = Depends(get_waste_svc),
) -> APIResponse[WasteCostByCategoryOutput]:
    """Waste cost breakdown by category with percentage of total."""
    return APIResponse(data=await svc.by_category(from_date, to_date))


# ── Cross-module reports ──────────────────────────────────────────────────────

@router.get(
    "/overview/sales-vs-purchasing",
    response_model=APIResponse[list[SalesVsPurchasingRow]],
)
async def sales_vs_purchasing(
    months: int = Query(default=7, ge=1, le=24),
    svc: CrossModuleReportService = Depends(get_cross_svc),
) -> APIResponse[list[SalesVsPurchasingRow]]:
    """
    Month-by-month gross margin: sales revenue minus purchasing spend.
    Covers the last N months.
    """
    return APIResponse(data=await svc.sales_vs_purchasing(months))


@router.get(
    "/overview/top-consumed",
    response_model=APIResponse[list[TopConsumedIngredientRow]],
)
async def top_consumed_ingredients(
    from_date: date = Query(default_factory=_default_period_start),
    to_date: date = Query(default_factory=_default_period_end),
    limit: int = Query(default=10, ge=1, le=50),
    svc: CrossModuleReportService = Depends(get_cross_svc),
) -> APIResponse[list[TopConsumedIngredientRow]]:
    """
    Top N ingredients by total quantity consumed (sales + production + waste exits)
    in the period.
    """
    return APIResponse(data=await svc.top_consumed_ingredients(from_date, to_date, limit))
