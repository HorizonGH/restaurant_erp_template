from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.models import Category, Ingredient, UnitOfMeasure
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.domain.models import Batch, KardexEntry, Location, StockItem, StockMovement
from app.modules.purchasing.domain.enums import POStatus
from app.modules.purchasing.domain.models import PurchaseOrder
from app.modules.sales.domain.enums import SalesChannel, SalesOrderStatus
from app.modules.sales.domain.models import SalesOrder, SalesOrderLine
from app.modules.waste.domain.models import WasteCategory, WasteRecord
from app.modules.reporting.application.schemas import (
    ExpiringBatchRow,
    InventoryValueByCategoryOutput,
    InventoryValueByCategoryRow,
    InventoryValueOutput,
    InventoryValueRow,
    LowStockRow,
    MonthlySalesRow,
    MonthlyPurchasingRow,
    PurchasingSummaryOutput,
    SalesByChannelOutput,
    SalesByChannelRow,
    SalesSummaryOutput,
    SalesVsPurchasingRow,
    TopConsumedIngredientRow,
    WasteCostByCategoryOutput,
    WasteCostByCategoryRow,
    WasteCostSummaryOutput,
)


_ZERO = Decimal("0")


class SalesReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, period_start: date, period_end: date) -> SalesSummaryOutput:
        stmt = (
            select(
                func.count(SalesOrder.entity_id).label("total"),
                func.coalesce(
                    func.sum(case(
                        (SalesOrder.status == SalesOrderStatus.delivered, 1), else_=0
                    )),
                    0,
                ).label("delivered"),
                func.coalesce(
                    func.sum(case(
                        (SalesOrder.status == SalesOrderStatus.cancelled, 1), else_=0
                    )),
                    0,
                ).label("cancelled"),
                func.coalesce(
                    func.sum(SalesOrder.total_amount).filter(
                        SalesOrder.status == SalesOrderStatus.delivered
                    ),
                    _ZERO,
                ).label("revenue"),
            )
            .where(
                SalesOrder.is_deleted.is_(False),
                func.date(SalesOrder.created_at) >= period_start,
                func.date(SalesOrder.created_at) <= period_end,
            )
        )
        row = (await self.session.execute(stmt)).one()

        total = row.total or 0
        delivered = int(row.delivered or 0)
        cancelled = int(row.cancelled or 0)
        revenue = row.revenue or _ZERO
        avg = (revenue / delivered) if delivered > 0 else _ZERO

        return SalesSummaryOutput(
            period_start=period_start,
            period_end=period_end,
            total_orders=total,
            delivered_orders=delivered,
            cancelled_orders=cancelled,
            gross_revenue=revenue,
            avg_order_value=avg,
        )

    async def by_channel(self, period_start: date, period_end: date) -> SalesByChannelOutput:
        stmt = (
            select(
                SalesOrder.channel,
                func.count(SalesOrder.entity_id).label("order_count"),
                func.coalesce(func.sum(SalesOrder.total_amount), _ZERO).label("revenue"),
            )
            .where(
                SalesOrder.is_deleted.is_(False),
                SalesOrder.status == SalesOrderStatus.delivered,
                func.date(SalesOrder.created_at) >= period_start,
                func.date(SalesOrder.created_at) <= period_end,
            )
            .group_by(SalesOrder.channel)
            .order_by(func.sum(SalesOrder.total_amount).desc())
        )
        rows = (await self.session.execute(stmt)).all()

        total_revenue = sum((r.revenue for r in rows), _ZERO)
        channel_rows = [
            SalesByChannelRow(
                channel=r.channel.value if hasattr(r.channel, "value") else str(r.channel),
                order_count=r.order_count,
                revenue=r.revenue,
                revenue_pct=(r.revenue / total_revenue * 100) if total_revenue else _ZERO,
            )
            for r in rows
        ]
        return SalesByChannelOutput(
            period_start=period_start,
            period_end=period_end,
            rows=channel_rows,
        )

    async def monthly_trend(self, months: int = 7) -> list[MonthlySalesRow]:
        stmt = (
            select(
                func.extract("year", SalesOrder.created_at).label("year"),
                func.extract("month", SalesOrder.created_at).label("month"),
                func.coalesce(func.sum(SalesOrder.total_amount), _ZERO).label("revenue"),
                func.count(SalesOrder.entity_id).label("order_count"),
            )
            .where(
                SalesOrder.is_deleted.is_(False),
                SalesOrder.status == SalesOrderStatus.delivered,
                SalesOrder.created_at >= _months_ago(months),
            )
            .group_by(
                func.extract("year", SalesOrder.created_at),
                func.extract("month", SalesOrder.created_at),
            )
            .order_by(
                func.extract("year", SalesOrder.created_at),
                func.extract("month", SalesOrder.created_at),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            MonthlySalesRow(
                year=int(r.year),
                month=int(r.month),
                revenue=r.revenue,
                order_count=r.order_count,
            )
            for r in rows
        ]


class PurchasingReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, period_start: date, period_end: date) -> PurchasingSummaryOutput:
        stmt = (
            select(
                func.count(PurchaseOrder.entity_id).label("total"),
                func.coalesce(
                    func.sum(case(
                        (PurchaseOrder.status.in_([
                            POStatus.sent, POStatus.partially_received, POStatus.received
                        ]), 1),
                        else_=0,
                    )),
                    0,
                ).label("sent"),
                func.coalesce(
                    func.sum(case(
                        (PurchaseOrder.status == POStatus.received, 1), else_=0
                    )),
                    0,
                ).label("received"),
                func.coalesce(func.sum(PurchaseOrder.total_amount), _ZERO).label("spend"),
            )
            .where(
                PurchaseOrder.is_deleted.is_(False),
                func.date(PurchaseOrder.created_at) >= period_start,
                func.date(PurchaseOrder.created_at) <= period_end,
            )
        )
        row = (await self.session.execute(stmt)).one()
        total = row.total or 0
        spend = row.spend or _ZERO
        avg = (spend / total) if total > 0 else _ZERO
        return PurchasingSummaryOutput(
            period_start=period_start,
            period_end=period_end,
            total_orders=total,
            sent_orders=int(row.sent or 0),
            received_orders=int(row.received or 0),
            total_spend=spend,
            avg_order_value=avg,
        )

    async def monthly_trend(self, months: int = 7) -> list[MonthlyPurchasingRow]:
        stmt = (
            select(
                func.extract("year", PurchaseOrder.created_at).label("year"),
                func.extract("month", PurchaseOrder.created_at).label("month"),
                func.coalesce(func.sum(PurchaseOrder.total_amount), _ZERO).label("spend"),
                func.count(PurchaseOrder.entity_id).label("order_count"),
            )
            .where(
                PurchaseOrder.is_deleted.is_(False),
                PurchaseOrder.created_at >= _months_ago(months),
            )
            .group_by(
                func.extract("year", PurchaseOrder.created_at),
                func.extract("month", PurchaseOrder.created_at),
            )
            .order_by(
                func.extract("year", PurchaseOrder.created_at),
                func.extract("month", PurchaseOrder.created_at),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            MonthlyPurchasingRow(
                year=int(r.year),
                month=int(r.month),
                spend=r.spend,
                order_count=r.order_count,
            )
            for r in rows
        ]


class InventoryReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def inventory_value(self, location_id: UUID | None = None) -> InventoryValueOutput:
        """
        Current inventory value = quantity_on_hand × last known unit_cost from kardex.
        Falls back to ingredient.cost_per_unit when no kardex entry exists.
        """
        # Subquery: last unit_cost per (ingredient, location) from kardex
        last_cost_sq = (
            select(
                KardexEntry.ingredient_id,
                KardexEntry.location_id,
                KardexEntry.unit_cost,
            )
            .distinct(KardexEntry.ingredient_id, KardexEntry.location_id)
            .order_by(
                KardexEntry.ingredient_id,
                KardexEntry.location_id,
                KardexEntry.movement_date.desc(),
            )
            .subquery("last_cost")
        )

        filters = [
            StockItem.is_deleted.is_(False),
            StockItem.quantity_on_hand > _ZERO,
            Location.is_deleted.is_(False),
            Ingredient.is_deleted.is_(False),
        ]
        if location_id is not None:
            filters.append(StockItem.location_id == location_id)

        stmt = (
            select(
                StockItem.location_id,
                Location.name.label("location_name"),
                StockItem.ingredient_id,
                Ingredient.name.label("ingredient_name"),
                Ingredient.sku,
                StockItem.quantity_on_hand,
                func.coalesce(last_cost_sq.c.unit_cost, Ingredient.cost_per_unit).label("unit_cost"),
            )
            .join(Location, StockItem.location_id == Location.entity_id)
            .join(Ingredient, StockItem.ingredient_id == Ingredient.entity_id)
            .outerjoin(
                last_cost_sq,
                (last_cost_sq.c.ingredient_id == StockItem.ingredient_id)
                & (last_cost_sq.c.location_id == StockItem.location_id),
            )
            .where(*filters)
            .order_by(Location.name, Ingredient.name)
        )

        rows = (await self.session.execute(stmt)).all()
        value_rows = [
            InventoryValueRow(
                location_id=r.location_id,
                location_name=r.location_name,
                ingredient_id=r.ingredient_id,
                ingredient_name=r.ingredient_name,
                sku=r.sku,
                quantity_on_hand=r.quantity_on_hand,
                unit_cost=r.unit_cost,
                total_value=r.quantity_on_hand * r.unit_cost,
            )
            for r in rows
        ]
        total = sum(r.total_value for r in value_rows)
        return InventoryValueOutput(
            as_of=date.today(),
            total_value=total,
            rows=value_rows,
        )

    async def inventory_value_by_category(self) -> InventoryValueByCategoryOutput:
        last_cost_sq = (
            select(
                KardexEntry.ingredient_id,
                KardexEntry.location_id,
                KardexEntry.unit_cost,
            )
            .distinct(KardexEntry.ingredient_id, KardexEntry.location_id)
            .order_by(
                KardexEntry.ingredient_id,
                KardexEntry.location_id,
                KardexEntry.movement_date.desc(),
            )
            .subquery("last_cost2")
        )

        stmt = (
            select(
                Category.entity_id.label("category_id"),
                Category.name.label("category_name"),
                func.count(func.distinct(StockItem.ingredient_id)).label("ingredient_count"),
                func.coalesce(func.sum(StockItem.quantity_on_hand), _ZERO).label("total_quantity"),
                func.coalesce(
                    func.sum(
                        StockItem.quantity_on_hand
                        * func.coalesce(last_cost_sq.c.unit_cost, Ingredient.cost_per_unit)
                    ),
                    _ZERO,
                ).label("total_value"),
            )
            .join(Ingredient, StockItem.ingredient_id == Ingredient.entity_id)
            .join(Category, Ingredient.category_id == Category.entity_id)
            .outerjoin(
                last_cost_sq,
                (last_cost_sq.c.ingredient_id == StockItem.ingredient_id)
                & (last_cost_sq.c.location_id == StockItem.location_id),
            )
            .where(
                StockItem.is_deleted.is_(False),
                StockItem.quantity_on_hand > _ZERO,
                Ingredient.is_deleted.is_(False),
                Category.is_deleted.is_(False),
            )
            .group_by(Category.entity_id, Category.name)
            .order_by(func.sum(
                StockItem.quantity_on_hand
                * func.coalesce(last_cost_sq.c.unit_cost, Ingredient.cost_per_unit)
            ).desc())
        )

        rows = (await self.session.execute(stmt)).all()
        cat_rows = [
            InventoryValueByCategoryRow(
                category_id=r.category_id,
                category_name=r.category_name,
                ingredient_count=r.ingredient_count,
                total_quantity=r.total_quantity,
                total_value=r.total_value,
            )
            for r in rows
        ]
        total = sum(r.total_value for r in cat_rows)
        return InventoryValueByCategoryOutput(
            as_of=date.today(),
            total_value=total,
            rows=cat_rows,
        )

    async def low_stock(self) -> list[LowStockRow]:
        stmt = (
            select(
                StockItem.ingredient_id,
                Ingredient.sku,
                Ingredient.name.label("ingredient_name"),
                StockItem.location_id,
                Location.name.label("location_name"),
                StockItem.quantity_on_hand,
                Ingredient.reorder_point,
            )
            .join(Ingredient, StockItem.ingredient_id == Ingredient.entity_id)
            .join(Location, StockItem.location_id == Location.entity_id)
            .where(
                StockItem.is_deleted.is_(False),
                Ingredient.is_deleted.is_(False),
                Location.is_deleted.is_(False),
                StockItem.quantity_on_hand <= Ingredient.reorder_point,
                Ingredient.reorder_point > _ZERO,
            )
            .order_by(
                (Ingredient.reorder_point - StockItem.quantity_on_hand).desc()
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LowStockRow(
                ingredient_id=r.ingredient_id,
                sku=r.sku,
                ingredient_name=r.ingredient_name,
                location_id=r.location_id,
                location_name=r.location_name,
                quantity_on_hand=r.quantity_on_hand,
                reorder_point=r.reorder_point,
                shortfall=r.reorder_point - r.quantity_on_hand,
            )
            for r in rows
        ]

    async def expiring_soon(self, days: int = 7) -> list[ExpiringBatchRow]:
        cutoff = date.today() + timedelta(days=days)
        stmt = (
            select(
                Batch.entity_id.label("batch_id"),
                Batch.batch_number,
                Batch.ingredient_id,
                Ingredient.name.label("ingredient_name"),
                Ingredient.sku,
                Batch.location_id,
                Location.name.label("location_name"),
                Batch.quantity,
                Batch.expiry_date,
            )
            .join(Ingredient, Batch.ingredient_id == Ingredient.entity_id)
            .join(Location, Batch.location_id == Location.entity_id)
            .where(
                Batch.is_deleted.is_(False),
                Batch.quantity > _ZERO,
                Batch.expiry_date.is_not(None),
                Batch.expiry_date <= cutoff,
                Ingredient.is_deleted.is_(False),
                Location.is_deleted.is_(False),
            )
            .order_by(Batch.expiry_date.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        today = date.today()
        return [
            ExpiringBatchRow(
                batch_id=r.batch_id,
                batch_number=r.batch_number,
                ingredient_id=r.ingredient_id,
                ingredient_name=r.ingredient_name,
                sku=r.sku,
                location_id=r.location_id,
                location_name=r.location_name,
                quantity=r.quantity,
                expiry_date=r.expiry_date,
                days_until_expiry=(r.expiry_date - today).days,
            )
            for r in rows
        ]


class WasteReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, period_start: date, period_end: date) -> WasteCostSummaryOutput:
        stmt = (
            select(
                func.count(WasteRecord.entity_id).label("total_records"),
                func.coalesce(func.sum(WasteRecord.quantity), _ZERO).label("total_quantity"),
                func.coalesce(
                    func.sum(WasteRecord.quantity * WasteRecord.unit_cost), _ZERO
                ).label("total_cost"),
            )
            .where(
                WasteRecord.is_deleted.is_(False),
                WasteRecord.waste_date >= period_start,
                WasteRecord.waste_date <= period_end,
            )
        )
        row = (await self.session.execute(stmt)).one()
        return WasteCostSummaryOutput(
            period_start=period_start,
            period_end=period_end,
            total_records=row.total_records or 0,
            total_quantity=row.total_quantity,
            total_cost=row.total_cost,
        )

    async def by_category(
        self, period_start: date, period_end: date
    ) -> WasteCostByCategoryOutput:
        stmt = (
            select(
                WasteCategory.entity_id.label("category_id"),
                WasteCategory.name.label("category_name"),
                func.count(WasteRecord.entity_id).label("record_count"),
                func.coalesce(func.sum(WasteRecord.quantity), _ZERO).label("total_quantity"),
                func.coalesce(
                    func.sum(WasteRecord.quantity * WasteRecord.unit_cost), _ZERO
                ).label("total_cost"),
            )
            .join(WasteRecord, WasteRecord.waste_category_id == WasteCategory.entity_id)
            .where(
                WasteRecord.is_deleted.is_(False),
                WasteCategory.is_deleted.is_(False),
                WasteRecord.waste_date >= period_start,
                WasteRecord.waste_date <= period_end,
            )
            .group_by(WasteCategory.entity_id, WasteCategory.name)
            .order_by(func.sum(WasteRecord.quantity * WasteRecord.unit_cost).desc())
        )
        rows = (await self.session.execute(stmt)).all()
        total_cost = sum((r.total_cost for r in rows), _ZERO)
        cat_rows = [
            WasteCostByCategoryRow(
                category_id=r.category_id,
                category_name=r.category_name,
                record_count=r.record_count,
                total_quantity=r.total_quantity,
                total_cost=r.total_cost,
                cost_pct=(r.total_cost / total_cost * 100) if total_cost else _ZERO,
            )
            for r in rows
        ]
        return WasteCostByCategoryOutput(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            rows=cat_rows,
        )


class CrossModuleReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sales_vs_purchasing(self, months: int = 7) -> list[SalesVsPurchasingRow]:
        """Monthly revenue vs spend — gross margin per month."""
        cutoff = _months_ago(months)

        sales_sq = (
            select(
                func.extract("year", SalesOrder.created_at).label("year"),
                func.extract("month", SalesOrder.created_at).label("month"),
                func.coalesce(func.sum(SalesOrder.total_amount), _ZERO).label("revenue"),
            )
            .where(
                SalesOrder.is_deleted.is_(False),
                SalesOrder.status == SalesOrderStatus.delivered,
                SalesOrder.created_at >= cutoff,
            )
            .group_by(
                func.extract("year", SalesOrder.created_at),
                func.extract("month", SalesOrder.created_at),
            )
            .subquery("monthly_sales")
        )

        purchasing_sq = (
            select(
                func.extract("year", PurchaseOrder.created_at).label("year"),
                func.extract("month", PurchaseOrder.created_at).label("month"),
                func.coalesce(func.sum(PurchaseOrder.total_amount), _ZERO).label("spend"),
            )
            .where(
                PurchaseOrder.is_deleted.is_(False),
                PurchaseOrder.created_at >= cutoff,
            )
            .group_by(
                func.extract("year", PurchaseOrder.created_at),
                func.extract("month", PurchaseOrder.created_at),
            )
            .subquery("monthly_purchasing")
        )

        # Full outer join on year+month
        stmt = (
            select(
                func.coalesce(sales_sq.c.year, purchasing_sq.c.year).label("year"),
                func.coalesce(sales_sq.c.month, purchasing_sq.c.month).label("month"),
                func.coalesce(sales_sq.c.revenue, _ZERO).label("revenue"),
                func.coalesce(purchasing_sq.c.spend, _ZERO).label("spend"),
            )
            .select_from(sales_sq)
            .join(
                purchasing_sq,
                (sales_sq.c.year == purchasing_sq.c.year)
                & (sales_sq.c.month == purchasing_sq.c.month),
                isouter=True,
            )
        )

        rows = (await self.session.execute(stmt)).all()
        result = []
        for r in rows:
            revenue = r.revenue or _ZERO
            spend = r.spend or _ZERO
            margin = revenue - spend
            margin_pct = (margin / revenue * 100) if revenue else _ZERO
            result.append(
                SalesVsPurchasingRow(
                    year=int(r.year),
                    month=int(r.month),
                    sales_revenue=revenue,
                    purchasing_spend=spend,
                    gross_margin=margin,
                    margin_pct=margin_pct,
                )
            )
        result.sort(key=lambda x: (x.year, x.month))
        return result

    async def top_consumed_ingredients(
        self,
        period_start: date,
        period_end: date,
        limit: int = 10,
    ) -> list[TopConsumedIngredientRow]:
        """
        Ingredients with the highest total quantity consumed via exit movements
        (sales_deduction + production_consumption + waste) in the period.
        """
        exit_types = [
            MovementType.sales_deduction,
            MovementType.production_consumption,
            MovementType.waste,
            MovementType.exit,
        ]

        stmt = (
            select(
                StockMovement.ingredient_id,
                Ingredient.sku,
                Ingredient.name.label("ingredient_name"),
                UnitOfMeasure.abbreviation.label("unit_abbreviation"),
                func.sum(StockMovement.quantity).label("total_consumed"),
                func.count(StockMovement.entity_id).label("movement_count"),
            )
            .join(Ingredient, StockMovement.ingredient_id == Ingredient.entity_id)
            .join(UnitOfMeasure, Ingredient.unit_of_measure_id == UnitOfMeasure.entity_id)
            .where(
                StockMovement.is_deleted.is_(False),
                StockMovement.movement_type.in_(exit_types),
                func.date(StockMovement.created_at) >= period_start,
                func.date(StockMovement.created_at) <= period_end,
                Ingredient.is_deleted.is_(False),
            )
            .group_by(
                StockMovement.ingredient_id,
                Ingredient.sku,
                Ingredient.name,
                UnitOfMeasure.abbreviation,
            )
            .order_by(func.sum(StockMovement.quantity).desc())
            .limit(limit)
        )

        rows = (await self.session.execute(stmt)).all()
        return [
            TopConsumedIngredientRow(
                ingredient_id=r.ingredient_id,
                sku=r.sku,
                ingredient_name=r.ingredient_name,
                unit_abbreviation=r.unit_abbreviation,
                total_quantity_consumed=r.total_consumed,
                movement_count=r.movement_count,
            )
            for r in rows
        ]


# ── helpers ──────────────────────────────────────────────────────────────────

def _months_ago(n: int) -> date:
    today = date.today()
    total_months = today.year * 12 + (today.month - 1) - n
    return date(total_months // 12, total_months % 12 + 1, 1)
