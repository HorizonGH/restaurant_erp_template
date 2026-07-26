from __future__ import annotations

from app.core.shared.domain.exceptions import BadRequestException


class PONotDraftException(BadRequestException):
    error_code = "po_not_draft"


class PONotSentException(BadRequestException):
    error_code = "po_not_sent"


class POAlreadyCancelledException(BadRequestException):
    error_code = "po_already_cancelled"


class POAlreadyReceivedException(BadRequestException):
    error_code = "po_already_received"


class EmptyPOException(BadRequestException):
    error_code = "empty_purchase_order"


class ReceiptNotDraftException(BadRequestException):
    error_code = "receipt_not_draft"


class ReceiptAlreadyCompletedException(BadRequestException):
    error_code = "receipt_already_completed"


class EmptyReceiptException(BadRequestException):
    error_code = "empty_receipt"


class InvoiceAlreadyMatchedException(BadRequestException):
    error_code = "invoice_already_matched"
