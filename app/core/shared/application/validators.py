from typing import Annotated

from pydantic import AfterValidator, StringConstraints

StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def to_lower(value: str) -> str:
    return value.lower()


LowerStr = Annotated[str, AfterValidator(to_lower)]
