from __future__ import annotations

from sqlalchemy_filterset import OrderingField

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    Filter,
    NullsPosition,
    OrderingFilter,
)
from app.modules.purchasing.domain.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseOrderFilterSet(BaseFilterSet[PurchaseOrder]):
    supplier_id = Filter(PurchaseOrder.supplier_id)
    status = Filter(PurchaseOrder.status)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(PurchaseOrder.created_at, nulls=NullsPosition.last),
            "expected_delivery_date": OrderingField(
                PurchaseOrder.expected_delivery_date, nulls=NullsPosition.last
            ),
        }
    )


class PurchaseOrderLineFilterSet(BaseFilterSet[PurchaseOrderLine]):
    order_id = Filter(PurchaseOrderLine.order_id)
    ingredient_id = Filter(PurchaseOrderLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(PurchaseOrderLine.created_at, nulls=NullsPosition.last),
        }
    )


class GoodsReceiptFilterSet(BaseFilterSet[GoodsReceipt]):
    order_id = Filter(GoodsReceipt.order_id)
    destination_location_id = Filter(GoodsReceipt.destination_location_id)
    status = Filter(GoodsReceipt.status)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(GoodsReceipt.created_at, nulls=NullsPosition.last),
        }
    )


class GoodsReceiptLineFilterSet(BaseFilterSet[GoodsReceiptLine]):
    receipt_id = Filter(GoodsReceiptLine.receipt_id)
    ingredient_id = Filter(GoodsReceiptLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(GoodsReceiptLine.created_at, nulls=NullsPosition.last),
        }
    )


class PurchaseInvoiceFilterSet(BaseFilterSet[PurchaseInvoice]):
    order_id = Filter(PurchaseInvoice.order_id)
    status = Filter(PurchaseInvoice.status)
    ordering = OrderingFilter(
        fields={
            "invoice_date": OrderingField(PurchaseInvoice.invoice_date, nulls=NullsPosition.last),
            "due_date": OrderingField(PurchaseInvoice.due_date, nulls=NullsPosition.last),
            "created_at": OrderingField(PurchaseInvoice.created_at, nulls=NullsPosition.last),
        }
    )
