import enum


class UnitType(str, enum.Enum):
    weight = "weight"
    volume = "volume"
    unit = "unit"
    length = "length"
