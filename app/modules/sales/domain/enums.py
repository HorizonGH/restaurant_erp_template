from __future__ import annotations

import enum


class SalesChannel(str, enum.Enum):
    dine_in = "dine_in"
    takeaway = "takeaway"
    delivery = "delivery"
    online = "online"


class SalesOrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_preparation = "in_preparation"
    ready = "ready"
    delivered = "delivered"
    cancelled = "cancelled"
