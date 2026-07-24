class AppException(Exception):
    status_code: int = 400
    error_code: str = "bad_request"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        super().__init__(message)


class BadRequestException(AppException):
    status_code = 400
    error_code = "bad_request"


class UnauthorizedException(AppException):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenException(AppException):
    status_code = 403
    error_code = "forbidden"


class NotFoundException(AppException):
    status_code = 404
    error_code = "not_found"


class ConflictException(AppException):
    status_code = 409
    error_code = "conflict"
