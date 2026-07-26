from __future__ import annotations

from app.core.shared.domain.exceptions import BadRequestException


class WasteCategoryInUseException(BadRequestException):
    error_code = "waste_category_in_use"
