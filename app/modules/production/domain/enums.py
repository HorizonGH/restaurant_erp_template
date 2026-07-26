from __future__ import annotations

import enum


class ProductionOrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
