from __future__ import annotations

import enum


class TransferStatus(str, enum.Enum):
    draft = "draft"
    in_transit = "in_transit"
    completed = "completed"
    cancelled = "cancelled"


class PhysicalCountStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
