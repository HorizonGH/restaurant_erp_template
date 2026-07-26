from __future__ import annotations

from app.core.shared.domain.exceptions import BadRequestException


class RecipeInUseException(BadRequestException):
    error_code = "recipe_in_use"


class RecipeVersionConflictException(BadRequestException):
    error_code = "recipe_version_conflict"


class OrderNotDraftException(BadRequestException):
    error_code = "order_not_draft"


class OrderNotConfirmedException(BadRequestException):
    error_code = "order_not_confirmed"


class OrderNotInProgressException(BadRequestException):
    error_code = "order_not_in_progress"


class OrderAlreadyCompletedException(BadRequestException):
    error_code = "order_already_completed"


class OrderAlreadyCancelledException(BadRequestException):
    error_code = "order_already_cancelled"


class InsufficientStockForProductionException(BadRequestException):
    error_code = "insufficient_stock_for_production"


class EmptyRecipeException(BadRequestException):
    error_code = "empty_recipe"


class EmptyProductionOrderException(BadRequestException):
    error_code = "empty_production_order"
