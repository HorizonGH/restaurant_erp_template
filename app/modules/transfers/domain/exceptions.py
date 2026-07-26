from __future__ import annotations

from app.core.shared.domain.exceptions import BadRequestException


class TransferNotDraftException(BadRequestException):
    error_code = "transfer_not_draft"


class TransferNotInTransitException(BadRequestException):
    error_code = "transfer_not_in_transit"


class TransferAlreadyCancelledException(BadRequestException):
    error_code = "transfer_already_cancelled"


class TransferAlreadyCompletedException(BadRequestException):
    error_code = "transfer_already_completed"


class PhysicalCountNotInProgressException(BadRequestException):
    error_code = "count_not_in_progress"


class PhysicalCountAlreadyCompletedException(BadRequestException):
    error_code = "count_already_completed"


class EmptyTransferException(BadRequestException):
    error_code = "empty_transfer"


class EmptyPhysicalCountException(BadRequestException):
    error_code = "empty_physical_count"
