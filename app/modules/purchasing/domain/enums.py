from __future__ import annotations

import enum


class POStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    partially_received = "partially_received"
    received = "received"
    cancelled = "cancelled"


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    disputed = "disputed"
    paid = "paid"


class ReceiptStatus(str, enum.Enum):
    draft = "draft"
    completed = "completed"
    cancelled = "cancelled"
