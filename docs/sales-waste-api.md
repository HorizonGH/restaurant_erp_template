# Sales & Waste Modules — API Reference

The sales module manages the full order lifecycle from creation through delivery, firing inventory deduction movements at the point of delivery. The waste module records stock that was discarded before sale, linking every waste event to an immutable inventory movement.

---

## Business Concepts

| Concept | Description |
|---|---|
| **Sales Order** | A request to fulfil a set of items from a single source location via a specific channel. Auto-numbered `SO-YYYYMM-XXXXXX`. |
| **Sales Order Line** | One ingredient line on an order: ingredient, quantity, and agreed unit price. |
| **Sales Channel** | `dine_in` · `takeaway` · `delivery` · `online` |
| **Waste Category** | A named classification for the cause of waste (e.g. Spoilage, Trim Waste, Breakage). |
| **Waste Record** | A single waste event: ingredient, location, category, quantity, unit cost (snapshot), and a hard link to the stock movement that deducted the stock. |

---

## Sales Order Lifecycle

```
pending ──confirm──► confirmed ──start_preparation──► in_preparation ──mark_ready──► ready ──deliver──► delivered
   │         │                                                                                   (movements fired)
   │      raises if
   │   stock insufficient
   │
   └──cancel──► cancelled  (from any non-delivered state)
```

| Status | Meaning |
|---|---|
| `pending` | Order created; lines can be freely added/updated/removed. |
| `confirmed` | Stock availability verified. Adding/updating/removing lines resets the order to `pending`. |
| `in_preparation` | Kitchen is actively preparing the order. |
| `ready` | Order is ready for hand-off or pick-up. |
| `delivered` | Order handed to the customer; one `sales_deduction` exit movement fired per line. |
| `cancelled` | Order abandoned; no inventory movements fired. |

**Movement rule:** `sales_deduction` movements fire only on `deliver()`. Cancellation at any stage — including after confirmation — never touches inventory.

---

## Sales Endpoints

All endpoints are under `/api/v1/sales`.

### Orders

#### `GET /orders`
List orders (paginated).

| Query param | Type | Description |
|---|---|---|
| `page` | int | Page number (default 1) |
| `size` | int | Page size (default 20) |
| `source_location_id` | UUID | Filter by source location |
| `channel` | enum | Filter by channel (`dine_in`, `takeaway`, `delivery`, `online`) |
| `status` | enum | Filter by order status |
| `ordering` | string | Comma-separated field names; prefix `-` for descending |

**Response** `200 OK`
```json
{
  "data": {
    "items": [{ "order_number": "SO-202507-A1B2C3", "status": "delivered", ... }],
    "total": 42,
    "page": 1,
    "size": 20
  }
}
```

---

#### `POST /orders`
Create a new order (status: `pending`, `total_amount: 0`).

**Request body**
```json
{
  "source_location_id": "<uuid>",
  "channel": "dine_in",
  "table_reference": "T-04",
  "notes": "Allergy: no nuts"
}
```

**Response** `201 Created` — `SalesOrderOutput`

---

#### `GET /orders/{order_id}`
Get a single order.

**Response** `200 OK` — `SalesOrderOutput`

---

#### `PATCH /orders/{order_id}`
Update notes or table_reference. Allowed only when status is `pending` or `confirmed`.

**Request body** *(all fields optional)*
```json
{
  "table_reference": "T-08",
  "notes": "Extra bread requested"
}
```

**Response** `200 OK` — `SalesOrderOutput`

---

#### `DELETE /orders/{order_id}`
Soft-delete a sales order. Only possible when status is `pending` or `cancelled`.

**Response** `204 No Content`

---

#### `POST /orders/{order_id}/confirm`
`pending → confirmed`. Validates that:
- At least one line exists.
- All lines have sufficient stock in `source_location`.

**Response** `200 OK` — `SalesOrderOutput`

**Errors**

| Code | Meaning |
|---|---|
| `order_not_pending` | Order is not in `pending` status. |
| `empty_sales_order` | No lines on the order. |
| `insufficient_stock_for_sale` | One or more lines lack available stock; full shortage list returned. |

---

#### `POST /orders/{order_id}/prepare`
`confirmed → in_preparation`.

**Response** `200 OK` — `SalesOrderOutput`

**Error:** `order_not_confirmed` if order is not `confirmed`.

---

#### `POST /orders/{order_id}/ready`
`in_preparation → ready`.

**Response** `200 OK` — `SalesOrderOutput`

**Error:** `order_not_in_preparation` if order is not `in_preparation`.

---

#### `POST /orders/{order_id}/deliver`
`ready → delivered`. Fires one `sales_deduction` exit movement per line from the `source_location`.

**Response** `200 OK` — `SalesOrderOutput`

**Error:** `order_not_ready` if order is not `ready`.

---

#### `POST /orders/{order_id}/cancel`
Cancel the order from any non-delivered state. Does **not** fire any inventory movements.

**Response** `200 OK` — `SalesOrderOutput`

**Errors**

| Code | Meaning |
|---|---|
| `order_already_cancelled` | Order is already cancelled. |
| `order_already_delivered` | Delivered orders cannot be cancelled. |

---

### Order Lines

#### `GET /orders/{order_id}/lines`
List all lines on an order.

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "<uuid>",
      "order_id": "<uuid>",
      "ingredient_id": "<uuid>",
      "quantity": "1.500",
      "unit_price": "18.00",
      "line_total": "27.00"
    }
  ]
}
```

---

#### `POST /orders/{order_id}/lines`
Add a line. Allowed when order is `pending` or `confirmed`. Adding a line to a `confirmed` order resets it to `pending`.

**Request body**
```json
{
  "ingredient_id": "<uuid>",
  "quantity": 1.5,
  "unit_price": 18.00
}
```

**Response** `201 Created` — `SalesOrderLineOutput`

**Errors:** `order_not_pending` · `conflict` (ingredient already on order or inactive)

---

#### `PATCH /orders/{order_id}/lines/{line_id}`
Update quantity or unit_price. Resets a `confirmed` order to `pending`.

**Request body** *(all optional)*
```json
{
  "quantity": 2.0,
  "unit_price": 17.50
}
```

**Response** `200 OK` — `SalesOrderLineOutput`

---

#### `DELETE /orders/{order_id}/lines/{line_id}`
Remove a line. Resets a `confirmed` order to `pending`.

**Response** `204 No Content`

---

## Waste Endpoints

All endpoints are under `/api/v1/waste`.

### Categories

#### `GET /categories/select`
Return all active categories as a flat list (for dropdowns).

**Response** `200 OK`
```json
{ "data": [{ "entity_id": "<uuid>", "name": "Spoilage", "description": "..." }] }
```

---

#### `GET /categories`
Paginated list with optional name search.

| Query param | Type | Description |
|---|---|---|
| `page` / `size` | int | Pagination |
| `name` | string | Partial match (ILIKE `%value%`) |
| `ordering` | string | `name`, `created_at` (prefix `-` for desc) |

**Response** `200 OK` — `Page[WasteCategoryOutput]`

---

#### `POST /categories`
Create a new category. Name must be unique.

**Request body**
```json
{
  "name": "Spoilage",
  "description": "Items that have expired or gone off before use"
}
```

**Response** `201 Created` — `WasteCategoryOutput`

**Error:** `conflict` if name already exists.

---

#### `GET /categories/{category_id}`
Get a single category.

**Response** `200 OK` — `WasteCategoryOutput`

---

#### `PATCH /categories/{category_id}`
Update name or description.

**Response** `200 OK` — `WasteCategoryOutput`

---

#### `DELETE /categories/{category_id}`
Soft-delete a category. Blocked if any waste records reference it.

**Response** `204 No Content`

**Error:** `waste_category_in_use`

---

### Records

#### `GET /records/summary`
Aggregate waste by category. Returns total quantity, total cost, and record count per category. Useful for cost reporting.

| Query param | Type | Description |
|---|---|---|
| `from_date` | date (`YYYY-MM-DD`) | Filter records on or after this date |
| `to_date` | date | Filter records on or before this date |
| `location_id` | UUID | Limit to a specific location |
| `waste_category_id` | UUID | Limit to a specific category |

**Response** `200 OK`
```json
{
  "data": [
    {
      "waste_category_id": "<uuid>",
      "category_name": "Spoilage",
      "total_quantity": "2.30",
      "total_cost": "18.40",
      "record_count": 3
    }
  ]
}
```

---

#### `GET /records`
Paginated list of waste records.

| Query param | Type | Description |
|---|---|---|
| `page` / `size` | int | Pagination |
| `ingredient_id` | UUID | Filter by ingredient |
| `location_id` | UUID | Filter by location |
| `waste_category_id` | UUID | Filter by category |
| `waste_date__gte` | date | Records on or after |
| `waste_date__lte` | date | Records on or before |
| `ordering` | string | `waste_date`, `created_at` (prefix `-` for desc) |

**Response** `200 OK` — `Page[WasteRecordOutput]`

---

#### `POST /records`
Record a waste event. This is a **single-step write** that:
1. Validates ingredient, location, and category.
2. Fires a `waste` exit movement against the ingredient's stock.
3. Snapshots `unit_cost` from the last kardex entry.
4. Creates an immutable `WasteRecord` with a hard link to the movement.

**Request body**
```json
{
  "ingredient_id": "<uuid>",
  "location_id": "<uuid>",
  "waste_category_id": "<uuid>",
  "quantity": 0.5,
  "waste_date": "2025-07-25",
  "reason": "Near-expiry spinach discarded",
  "notes": "Three bags with yellowing leaves removed from morning mise en place"
}
```

**Response** `201 Created`
```json
{
  "data": {
    "entity_id": "<uuid>",
    "ingredient_id": "<uuid>",
    "location_id": "<uuid>",
    "waste_category_id": "<uuid>",
    "movement_id": "<uuid>",
    "quantity": "0.5000",
    "unit_cost": "3.50",
    "total_cost": "1.75",
    "waste_date": "2025-07-25",
    "reason": "Near-expiry spinach discarded",
    "notes": "Three bags with yellowing leaves removed from morning mise en place"
  }
}
```

**Errors**

| Code | Meaning |
|---|---|
| `not_found` | Ingredient, location, or category does not exist. |
| `insufficient_stock` | Not enough stock at the location to record the waste quantity. |

---

#### `GET /records/{record_id}`
Get a single waste record.

**Response** `200 OK` — `WasteRecordOutput`

---

## Error Reference

| `error_code` | HTTP | Trigger |
|---|---|---|
| `order_not_pending` | 400 | Transition or line mutation requires `pending` status |
| `order_not_confirmed` | 400 | `start_preparation` called on non-`confirmed` order |
| `order_not_in_preparation` | 400 | `mark_ready` called on non-`in_preparation` order |
| `order_not_ready` | 400 | `deliver` called on non-`ready` order |
| `order_already_cancelled` | 400 | `cancel` called on already-cancelled order |
| `order_already_delivered` | 400 | `cancel` or second `deliver` called on delivered order |
| `empty_sales_order` | 400 | `confirm` or `deliver` called with no lines |
| `insufficient_stock_for_sale` | 400 | `confirm` fails; lists all shortages |
| `waste_category_in_use` | 400 | Delete category that has waste records |
| `insufficient_stock` | 400 | Waste quantity exceeds available stock |
| `conflict` | 409 | Duplicate ingredient line, inactive ingredient, or duplicate category name |
| `not_found` | 404 | Requested entity does not exist |

---

## End-to-End Example

The following bash script walks through a complete dine-in order and a waste event.

```bash
BASE="http://localhost:8000/api/v1"

# ── Resolve IDs ──────────────────────────────────────────────────────────────
FRDG=$(curl -s "$BASE/inventory/locations?code=FRG-01" | jq -r '.data.items[0].entity_id')
POL_ID=$(curl -s "$BASE/catalog/ingredients?sku=POL-001" | jq -r '.data.items[0].entity_id')
VEG_ID=$(curl -s "$BASE/catalog/ingredients?sku=VEG-001" | jq -r '.data.items[0].entity_id')
SPOILAGE_ID=$(curl -s "$BASE/waste/categories?name=Spoilage" | jq -r '.data.items[0].entity_id')

# ── Create order ─────────────────────────────────────────────────────────────
ORDER=$(curl -s -X POST "$BASE/sales/orders" \
  -H "Content-Type: application/json" \
  -d "{\"source_location_id\":\"$FRDG\",\"channel\":\"dine_in\",\"table_reference\":\"T-12\"}")
ORDER_ID=$(echo $ORDER | jq -r '.data.entity_id')
echo "Order: $ORDER_ID"

# ── Add lines ────────────────────────────────────────────────────────────────
curl -s -X POST "$BASE/sales/orders/$ORDER_ID/lines" \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_id\":\"$POL_ID\",\"quantity\":1.5,\"unit_price\":18.00}" | jq .data.line_total

curl -s -X POST "$BASE/sales/orders/$ORDER_ID/lines" \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_id\":\"$VEG_ID\",\"quantity\":0.5,\"unit_price\":4.50}" | jq .data.line_total

# ── Full lifecycle ────────────────────────────────────────────────────────────
curl -s -X POST "$BASE/sales/orders/$ORDER_ID/confirm"  | jq .data.status
curl -s -X POST "$BASE/sales/orders/$ORDER_ID/prepare"  | jq .data.status
curl -s -X POST "$BASE/sales/orders/$ORDER_ID/ready"    | jq .data.status
curl -s -X POST "$BASE/sales/orders/$ORDER_ID/deliver"  | jq .data.status
# → "delivered"

# ── Record waste (spinach spoilage) ──────────────────────────────────────────
curl -s -X POST "$BASE/waste/records" \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$(curl -s "$BASE/catalog/ingredients?sku=VEG-006" | jq -r '.data.items[0].entity_id')\",
    \"location_id\": \"$FRDG\",
    \"waste_category_id\": \"$SPOILAGE_ID\",
    \"quantity\": 0.5,
    \"waste_date\": \"$(date +%Y-%m-%d)\",
    \"reason\": \"Near-expiry spinach discarded\"
  }" | jq '{total_cost: .data.total_cost, movement_id: .data.movement_id}'

# ── Waste summary ─────────────────────────────────────────────────────────────
curl -s "$BASE/waste/records/summary?from_date=$(date +%Y-%m-01)" | jq .data
```
