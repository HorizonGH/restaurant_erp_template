# Purchasing Module — API Reference

The purchasing module covers the full procure-to-pay cycle: creating purchase orders, sending them to suppliers, receiving goods into inventory, and managing supplier invoices.

---

## Business Concepts

| Concept | Description |
|---|---|
| **Purchase Order (PO)** | An authorised request to buy specific quantities of ingredients from a supplier at an agreed unit cost. Auto-numbered `PO-YYYYMM-XXXXX`. |
| **Goods Receipt** | Records the physical arrival of goods. Each receipt links to a PO and a destination location. Completing a receipt triggers inventory entry movements. |
| **Purchase Invoice** | The supplier's billing document. After verification it is matched to the PO; once matched it can be marked paid. |

---

## Purchase Order Lifecycle

```
draft ──send──► sent ──partial receipt──► partially_received ──all lines received──► received
  │                │                              │
  └──cancel──► cancelled    └──cancel──► cancelled
```

| Status | Meaning |
|---|---|
| `draft` | Being built. Lines can be added/edited/removed. |
| `sent` | Submitted to supplier. No more line edits. Goods receipts can be created. |
| `partially_received` | At least one line has been partially or fully received. |
| `received` | All lines fully received. |
| `cancelled` | Voided before full receipt. |

---

## Goods Receipt Lifecycle

```
draft ──complete──► completed
  │
  └──cancel──► cancelled
```

Completing a receipt:
1. Creates an inventory **entry** movement per line (`reference_type = "goods_receipt"`).
2. Updates `received_quantity` on each matching PO line.
3. Recalculates the PO status (`partially_received` or `received`).

---

## Invoice Lifecycle

```
pending ──match──► matched ──pay──► paid
    │
    └──dispute──► disputed
```

| Status | Meaning |
|---|---|
| `pending` | Invoice received, not yet verified. |
| `matched` | Amounts reconciled against PO / receipt. |
| `disputed` | Discrepancy found; supplier notified. |
| `paid` | Payment sent (or scheduled). |

---

## Base URL

```
/api/v1/purchasing
```

---

## Purchase Orders

### List orders

```
GET /orders
```

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `page` | int | Page number (default 1) |
| `size` | int | Page size (default 20, max 100) |
| `supplier_id` | UUID | Filter by supplier |
| `status` | string | Filter by PO status |
| `ordering` | string | `created_at`, `expected_delivery_date` (prefix `-` for desc) |

**Response** `200 OK`
```json
{
  "data": {
    "items": [
      {
        "entity_id": "b3e2a1d0-...",
        "po_number": "PO-202507-A1B2C",
        "supplier_id": "sup-uuid",
        "status": "sent",
        "expected_delivery_date": "2025-07-28",
        "notes": null,
        "total_amount": "375.00"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

---

### Create a purchase order

```
POST /orders
```

**Body**
```json
{
  "supplier_id": "sup-uuid",
  "expected_delivery_date": "2025-07-30",
  "notes": "Urgent — low stock on beef"
}
```

**Response** `201 Created`

---

### Get order

```
GET /orders/{order_id}
```

---

### Update order

```
PATCH /orders/{order_id}
```

Only allowed when status is `draft` or `sent`. Only `expected_delivery_date` and `notes` can be changed.

---

### Send order

```
POST /orders/{order_id}/send
```

Transitions the PO from `draft` → `sent`. Requires at least one line.

**Errors**

| Code | Meaning |
|---|---|
| `po_not_draft` | PO is not in draft status |
| `empty_purchase_order` | PO has no lines |

---

### Cancel order

```
POST /orders/{order_id}/cancel
```

Can cancel any non-`received` order.

---

## Purchase Order Lines

### List lines

```
GET /orders/{order_id}/lines
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "line-uuid",
      "order_id": "po-uuid",
      "ingredient_id": "ing-uuid",
      "ordered_quantity": "15.0000",
      "received_quantity": "15.0000",
      "unit_cost": "25.0000",
      "line_total": "375.0000",
      "is_fully_received": true
    }
  ]
}
```

---

### Add line

```
POST /orders/{order_id}/lines
```

PO must be in `draft`.

**Body**
```json
{
  "ingredient_id": "ing-uuid",
  "ordered_quantity": 15,
  "unit_cost": 25.00
}
```

**Response** `201 Created`

---

### Update line

```
PATCH /orders/{order_id}/lines/{line_id}
```

PO must be in `draft`. Fields: `ordered_quantity`, `unit_cost`.

---

### Remove line

```
DELETE /orders/{order_id}/lines/{line_id}
```

PO must be in `draft`. Returns `204 No Content`.

---

## Goods Receipts

### List receipts

```
GET /receipts
```

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `order_id` | UUID | Filter by PO |
| `destination_location_id` | UUID | Filter by destination |
| `status` | string | Filter by receipt status |

---

### Create receipt

```
POST /receipts
```

PO must be `sent` or `partially_received`.

**Body**
```json
{
  "order_id": "po-uuid",
  "destination_location_id": "loc-uuid",
  "notes": "Delivered at loading dock"
}
```

**Response** `201 Created`

---

### Get receipt

```
GET /receipts/{receipt_id}
```

---

### Update receipt

```
PATCH /receipts/{receipt_id}
```

Receipt must be `draft`. Only `notes` can be changed.

---

### Complete receipt

```
POST /receipts/{receipt_id}/complete
```

Fires inventory entry movements for all lines, updates PO line quantities, recalculates PO status.

**Errors**

| Code | Meaning |
|---|---|
| `receipt_not_draft` | Receipt is not in draft |
| `receipt_already_completed` | Already completed |
| `empty_receipt` | No lines added |

---

### Cancel receipt

```
POST /receipts/{receipt_id}/cancel
```

---

## Goods Receipt Lines

### List lines

```
GET /receipts/{receipt_id}/lines
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "rl-uuid",
      "receipt_id": "rcpt-uuid",
      "ingredient_id": "ing-uuid",
      "batch_number": "PO-202507-BEEF-001",
      "lot_number": "L2025-07A",
      "expiry_date": "2025-08-08",
      "received_quantity": "15.0000",
      "unit_cost": "25.0000",
      "line_total": "375.0000"
    }
  ]
}
```

---

### Add line

```
POST /receipts/{receipt_id}/lines
```

Receipt must be `draft`.

**Body**
```json
{
  "ingredient_id": "ing-uuid",
  "batch_number": "PO-202507-BEEF-001",
  "lot_number": "L2025-07A",
  "expiry_date": "2025-08-08",
  "received_quantity": 15,
  "unit_cost": 25.00
}
```

**Response** `201 Created`

---

### Update line

```
PATCH /receipts/{receipt_id}/lines/{line_id}
```

Receipt must be `draft`.

---

### Remove line

```
DELETE /receipts/{receipt_id}/lines/{line_id}
```

Receipt must be `draft`. Returns `204 No Content`.

---

## Invoices

### List invoices

```
GET /invoices
```

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `order_id` | UUID | Filter by PO |
| `status` | string | Filter by invoice status |
| `ordering` | string | `invoice_date`, `due_date`, `created_at` |

---

### Create invoice

```
POST /invoices
```

PO must not be in `draft` or `cancelled`.

**Body**
```json
{
  "order_id": "po-uuid",
  "invoice_number": "INV-SUPPLIER-20250728",
  "invoice_date": "2025-07-25",
  "due_date": "2025-08-24",
  "total_amount": 375.00,
  "notes": "Supplier invoice reference #98765"
}
```

**Response** `201 Created`

---

### Get invoice

```
GET /invoices/{invoice_id}
```

---

### Update invoice

```
PATCH /invoices/{invoice_id}
```

Cannot update a `matched` invoice. Fields: `due_date`, `notes`.

---

### Match invoice

```
POST /invoices/{invoice_id}/match
```

`pending` or `disputed` → `matched`. Confirms supplier amounts are correct against PO.

---

### Pay invoice

```
POST /invoices/{invoice_id}/pay
```

`matched` → `paid`.

---

### Dispute invoice

```
POST /invoices/{invoice_id}/dispute
```

`pending` or `matched` → `disputed`. Cannot dispute a `paid` invoice.

---

## Error Reference

| Error code | HTTP | When raised |
|---|---|---|
| `po_not_draft` | 400 | Operation requires draft status |
| `po_not_sent` | 400 | Receipt creation requires sent/partially received PO |
| `po_already_cancelled` | 400 | PO is already cancelled |
| `po_already_received` | 400 | Fully received PO cannot be cancelled |
| `empty_purchase_order` | 400 | Cannot send PO with no lines |
| `receipt_not_draft` | 400 | Operation requires draft receipt |
| `receipt_already_completed` | 400 | Receipt already completed |
| `empty_receipt` | 400 | Cannot complete receipt with no lines |
| `invoice_already_matched` | 400 | Cannot update or re-match a matched invoice |
| `not_found` | 404 | PO / receipt / invoice not found |
| `conflict` | 409 | Duplicate ingredient line or invoice number |

---

## End-to-End Example

```bash
BASE="http://localhost:8000/api/v1"

# 1. Create a draft PO
PO=$(curl -s -X POST "$BASE/purchasing/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "<supplier-uuid>",
    "expected_delivery_date": "2025-07-30",
    "notes": "Weekly meat order"
  }')
PO_ID=$(echo $PO | jq -r '.data.entity_id')
echo "Created PO: $PO_ID"

# 2. Add lines
curl -s -X POST "$BASE/purchasing/orders/$PO_ID/lines" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": "<beef-uuid>", "ordered_quantity": 15, "unit_cost": 25.00}'

curl -s -X POST "$BASE/purchasing/orders/$PO_ID/lines" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": "<pork-uuid>", "ordered_quantity": 10, "unit_cost": 8.20}'

# 3. Send PO to supplier
curl -s -X POST "$BASE/purchasing/orders/$PO_ID/send"

# 4. Create goods receipt when goods arrive
RCPT=$(curl -s -X POST "$BASE/purchasing/receipts" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\": \"$PO_ID\", \"destination_location_id\": \"<freezer-uuid>\"}")
RCPT_ID=$(echo $RCPT | jq -r '.data.entity_id')

# 5. Add receipt lines
curl -s -X POST "$BASE/purchasing/receipts/$RCPT_ID/lines" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "<beef-uuid>",
    "batch_number": "PO-20250730-BEEF",
    "lot_number": "L2025-07A",
    "expiry_date": "2025-08-14",
    "received_quantity": 15,
    "unit_cost": 25.00
  }'

curl -s -X POST "$BASE/purchasing/receipts/$RCPT_ID/lines" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "<pork-uuid>",
    "batch_number": "PO-20250730-PORK",
    "received_quantity": 10,
    "unit_cost": 8.20
  }'

# 6. Complete receipt — inventory entry movements fire here
curl -s -X POST "$BASE/purchasing/receipts/$RCPT_ID/complete"
# PO status → "received"

# 7. Register supplier invoice
INV=$(curl -s -X POST "$BASE/purchasing/invoices" \
  -H "Content-Type: application/json" \
  -d "{
    \"order_id\": \"$PO_ID\",
    \"invoice_number\": \"INV-MEATS-2025-001\",
    \"invoice_date\": \"2025-07-28\",
    \"due_date\": \"2025-08-27\",
    \"total_amount\": 457.00
  }")
INV_ID=$(echo $INV | jq -r '.data.entity_id')

# 8. Match and pay
curl -s -X POST "$BASE/purchasing/invoices/$INV_ID/match"
curl -s -X POST "$BASE/purchasing/invoices/$INV_ID/pay"
```
