import enum


class MovementType(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    adjustment = "adjustment"
    transfer_out = "transfer_out"
    transfer_in = "transfer_in"
    waste = "waste"
    production_consumption = "production_consumption"
    sales_deduction = "sales_deduction"
    physical_count = "physical_count"


class LocationType(str, enum.Enum):
    warehouse = "warehouse"
    fridge = "fridge"
    freezer = "freezer"
    bar = "bar"
    production = "production"
