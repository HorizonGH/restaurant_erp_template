from app.core.shared.domain.exceptions import BadRequestException, ConflictException


class DuplicateSKUException(ConflictException):
    error_code = "duplicate_sku"


class IngredientInUseException(BadRequestException):
    error_code = "ingredient_in_use"


class CategoryInUseException(BadRequestException):
    error_code = "category_in_use"
