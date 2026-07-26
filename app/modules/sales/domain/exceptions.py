from __future__ import annotations

from app.core.shared.domain.exceptions import BadRequestException


class OrderNotPendingException(BadRequestException):
    error_code = "order_not_pending"


class OrderNotConfirmedException(BadRequestException):
    error_code = "order_not_confirmed"


class OrderNotInPreparationException(BadRequestException):
    error_code = "order_not_in_preparation"


class OrderNotReadyException(BadRequestException):
    error_code = "order_not_ready"


class OrderAlreadyCancelledException(BadRequestException):
    error_code = "order_already_cancelled"


class OrderAlreadyDeliveredException(BadRequestException):
    error_code = "order_already_delivered"


class EmptySalesOrderException(BadRequestException):
    error_code = "empty_sales_order"


class InsufficientStockForSaleException(BadRequestException):
    error_code = "insufficient_stock_for_sale"
