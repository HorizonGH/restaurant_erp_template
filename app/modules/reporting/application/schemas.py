from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Sales ────────────────────────────────────────────────────────────────────

class SalesSummaryOutput(ReportSchema):
    period_start: date
    period_end: date
    total_orders: int
    delivered_orders: int
    cancelled_orders: int
    gross_revenue: Decimal
    avg_order_value: Decimal


class SalesByChannelRow(ReportSchema):
    channel: str
    order_count: int
    revenue: Decimal
    revenue_pct: Decimal


class SalesByChannelOutput(ReportSchema):
    period_start: date
    period_end: date
    rows: list[SalesByChannelRow]


class MonthlySalesRow(ReportSchema):
    year: int
    month: int
    revenue: Decimal
    order_count: int


# ── Purchasing ───────────────────────────────────────────────────────────────

class PurchasingSummaryOutput(ReportSchema):
    period_start: date
    period_end: date
    total_orders: int
    sent_orders: int
    received_orders: int
    total_spend: Decimal
    avg_order_value: Decimal


class MonthlyPurchasingRow(ReportSchema):
    year: int
    month: int
    spend: Decimal
    order_count: int


# ── Inventory ────────────────────────────────────────────────────────────────

class InventoryValueRow(ReportSchema):
    location_id: UUID
    location_name: str
    ingredient_id: UUID
    ingredient_name: str
    sku: str
    quantity_on_hand: Decimal
    unit_cost: Decimal
    total_value: Decimal


class InventoryValueOutput(ReportSchema):
    as_of: date
    total_value: Decimal
    rows: list[InventoryValueRow]


class InventoryValueByCategoryRow(ReportSchema):
    category_id: UUID
    category_name: str
    ingredient_count: int
    total_quantity: Decimal
    total_value: Decimal


class InventoryValueByCategoryOutput(ReportSchema):
    as_of: date
    total_value: Decimal
    rows: list[InventoryValueByCategoryRow]


class LowStockRow(ReportSchema):
    ingredient_id: UUID
    sku: str
    ingredient_name: str
    location_id: UUID
    location_name: str
    quantity_on_hand: Decimal
    reorder_point: Decimal
    shortfall: Decimal


class ExpiringBatchRow(ReportSchema):
    batch_id: UUID
    batch_number: str
    ingredient_id: UUID
    ingredient_name: str
    sku: str
    location_id: UUID
    location_name: str
    quantity: Decimal
    expiry_date: date
    days_until_expiry: int


# ── Waste ────────────────────────────────────────────────────────────────────

class WasteCostSummaryOutput(ReportSchema):
    period_start: date
    period_end: date
    total_records: int
    total_quantity: Decimal
    total_cost: Decimal


class WasteCostByCategoryRow(ReportSchema):
    category_id: UUID
    category_name: str
    record_count: int
    total_quantity: Decimal
    total_cost: Decimal
    cost_pct: Decimal


class WasteCostByCategoryOutput(ReportSchema):
    period_start: date
    period_end: date
    total_cost: Decimal
    rows: list[WasteCostByCategoryRow]


# ── Cross-module ─────────────────────────────────────────────────────────────

class SalesVsPurchasingRow(ReportSchema):
    year: int
    month: int
    sales_revenue: Decimal
    purchasing_spend: Decimal
    gross_margin: Decimal
    margin_pct: Decimal


class TopConsumedIngredientRow(ReportSchema):
    ingredient_id: UUID
    sku: str
    ingredient_name: str
    unit_abbreviation: str
    total_quantity_consumed: Decimal
    movement_count: int
