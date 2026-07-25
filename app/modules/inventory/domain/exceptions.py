from app.core.shared.domain.exceptions import BadRequestException


class InsufficientStockException(BadRequestException):
    error_code = "insufficient_stock"


class BatchExpiredException(BadRequestException):
    error_code = "batch_expired"


class LocationInUseException(BadRequestException):
    error_code = "location_in_use"
